/*
 * native_scanner.c — High-performance AOB (Array of Bytes) pattern scanner
 *
 * Provides a C-level scanning engine for finding byte patterns with wildcard
 * support in a target process's memory.  On Linux the scanner can read memory
 * directly via process_vm_readv(2); a buffer-based entry point is also
 * provided so the Python side can feed pre-read memory chunks.
 *
 * Compile:
 *   gcc -O2 -shared -fPIC -o native_scanner.so native_scanner.c
 */

#define _GNU_SOURCE
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <stdlib.h>

#ifdef __linux__
#include <sys/uio.h>   /* struct iovec, process_vm_readv */
#include <unistd.h>     /* getpid */
#endif

/* ------------------------------------------------------------------ */
/* Public constants                                                    */
/* ------------------------------------------------------------------ */

/** Wildcard sentinel — any value >= 256 is treated as a wildcard. */
#define WILDCARD 0xFFFF

/** Maximum number of results that can be returned per call. */
#define MAX_RESULTS 4096

/** Read-chunk size used by the process_vm_readv path (1 MiB). */
#define CHUNK_SIZE (1024 * 1024)

/* ------------------------------------------------------------------ */
/* Boyer-Moore-inspired skip table (honours wildcards)                 */
/* ------------------------------------------------------------------ */

/**
 * Build a skip table for the Bad-Character heuristic, adapted for
 * patterns that contain wildcards.
 *
 * For every byte value (0..255) we store the maximum safe shift when
 * that byte is found at the alignment position (last byte of the
 * window).  Wildcard positions can match ANY byte, so when a wildcard
 * appears at index *j* the skip for every byte value must be reduced
 * to at most ``pattern_len − 1 − j``.
 */
static void build_skip_table(
    const uint16_t *pattern,
    size_t          pattern_len,
    size_t          skip[256])
{
    size_t i, b;

    /* Default shift: full pattern length (no match possible). */
    for (i = 0; i < 256; i++)
        skip[i] = pattern_len;

    /*
     * Walk the pattern left-to-right (excluding the last byte).
     * For concrete bytes, record the distance from the end.
     * For wildcards, reduce the skip for ALL byte values since any
     * value could appear at a wildcard position.
     */
    for (i = 0; i < pattern_len - 1; i++) {
        if (pattern[i] < 256) {
            skip[pattern[i]] = pattern_len - 1 - i;
        } else {
            /* Wildcard: any byte could match here. */
            size_t s = pattern_len - 1 - i;
            for (b = 0; b < 256; b++) {
                if (skip[b] > s)
                    skip[b] = s;
            }
        }
    }
}

/* ------------------------------------------------------------------ */
/* Pattern matching helpers                                            */
/* ------------------------------------------------------------------ */

/**
 * Test whether `data[offset .. offset+pattern_len)` matches the pattern.
 * Wildcard entries (>= 256) always match.
 */
static int match_at(
    const uint8_t  *data,
    size_t          offset,
    const uint16_t *pattern,
    size_t          pattern_len)
{
    size_t i;
    for (i = 0; i < pattern_len; i++) {
        if (pattern[i] < 256 && data[offset + i] != (uint8_t)pattern[i])
            return 0;
    }
    return 1;
}

/* ------------------------------------------------------------------ */
/* Buffer-based AOB scan (works on any OS)                             */
/* ------------------------------------------------------------------ */

/**
 * aob_scan_buffer — scan a caller-supplied buffer for pattern matches.
 *
 * @param data          Pointer to the memory buffer to search.
 * @param data_len      Length of the buffer in bytes.
 * @param pattern       Pattern array. Values 0–255 are literal byte values;
 *                      values >= 256 (WILDCARD) are wildcards.
 * @param pattern_len   Number of entries in the pattern array.
 * @param base_address  Virtual address corresponding to data[0] — used to
 *                      compute result addresses.
 * @param out_addresses Caller-allocated array to receive matched addresses.
 * @param max_results   Size of out_addresses.
 *
 * @return Number of matches written to out_addresses.
 */
int aob_scan_buffer(
    const uint8_t  *data,
    size_t          data_len,
    const uint16_t *pattern,
    size_t          pattern_len,
    uint64_t        base_address,
    uint64_t       *out_addresses,
    size_t          max_results)
{
    size_t skip[256];
    size_t count = 0;
    size_t i;
    int    all_wild;

    if (!data || !pattern || pattern_len == 0 || data_len < pattern_len)
        return 0;

    /* Check whether the entire pattern is wildcards (degenerate case). */
    all_wild = 1;
    for (i = 0; i < pattern_len; i++) {
        if (pattern[i] < 256) { all_wild = 0; break; }
    }

    if (all_wild) {
        /* Every position trivially matches — just return up to max. */
        size_t limit = data_len - pattern_len + 1;
        if (limit > max_results) limit = max_results;
        for (i = 0; i < limit; i++)
            out_addresses[i] = base_address + i;
        return (int)limit;
    }

    /* Build the skip table for Boyer-Moore-like advancement. */
    build_skip_table(pattern, pattern_len, skip);

    /*
     * Main scan loop.
     *
     * We try a Boyer-Moore bad-character shift using the last byte of
     * the pattern.  If the last pattern byte is a wildcard we fall back
     * to a simple stride-1 advance.
     */
    i = 0;
    if (pattern[pattern_len - 1] < 256) {
        /* Last byte is a concrete value — use skip table. */
        while (i <= data_len - pattern_len && count < max_results) {
            uint8_t last = data[i + pattern_len - 1];
            if (last == (uint8_t)pattern[pattern_len - 1]) {
                if (match_at(data, i, pattern, pattern_len)) {
                    out_addresses[count++] = base_address + i;
                }
                i += 1;  /* advance past this match */
            } else {
                size_t s = skip[last];
                i += (s > 0) ? s : 1;
            }
        }
    } else {
        /* Last byte is a wildcard — simple linear scan. */
        while (i <= data_len - pattern_len && count < max_results) {
            if (match_at(data, i, pattern, pattern_len)) {
                out_addresses[count++] = base_address + i;
            }
            i += 1;
        }
    }

    return (int)count;
}

/* ------------------------------------------------------------------ */
/* Linux process_vm_readv-based scan                                   */
/* ------------------------------------------------------------------ */

#ifdef __linux__

/**
 * aob_scan_process — scan another process's virtual memory for a pattern.
 *
 * Uses process_vm_readv(2) to read memory in 1 MiB chunks and searches
 * each chunk (with overlap for cross-boundary matches).
 *
 * @param pid           Target process PID.
 * @param pattern       Pattern array (values >= 256 = wildcard).
 * @param pattern_len   Length of the pattern.
 * @param start_address First address to scan.
 * @param end_address   One-past-the-last address to scan.
 * @param out_addresses Caller-allocated result buffer.
 * @param max_results   Size of out_addresses.
 *
 * @return Number of matches found, or -1 on error.
 */
int aob_scan_process(
    int             pid,
    const uint16_t *pattern,
    size_t          pattern_len,
    uint64_t        start_address,
    uint64_t        end_address,
    uint64_t       *out_addresses,
    size_t          max_results)
{
    uint8_t *buf = NULL;
    size_t   total = 0;
    uint64_t addr;
    size_t   overlap;

    if (!pattern || pattern_len == 0 || start_address >= end_address)
        return 0;

    buf = (uint8_t *)malloc(CHUNK_SIZE + pattern_len);
    if (!buf)
        return -1;

    overlap = pattern_len - 1;
    addr    = start_address;

    while (addr < end_address && total < max_results) {
        size_t want = CHUNK_SIZE + overlap;
        if (addr + want > end_address)
            want = (size_t)(end_address - addr);
        if (want < pattern_len)
            break;

        /* Read from the target process via process_vm_readv. */
        struct iovec local  = { .iov_base = buf,           .iov_len = want };
        struct iovec remote = { .iov_base = (void *)addr,  .iov_len = want };

        ssize_t nread = process_vm_readv((pid_t)pid, &local, 1, &remote, 1, 0);
        if (nread <= 0 || (size_t)nread < pattern_len) {
            /* Unreadable region — skip forward. */
            addr += CHUNK_SIZE;
            continue;
        }

        int found = aob_scan_buffer(
            buf, (size_t)nread,
            pattern, pattern_len,
            addr,
            out_addresses + total,
            max_results - total);

        if (found > 0)
            total += (size_t)found;

        addr += CHUNK_SIZE;
    }

    free(buf);
    return (int)total;
}

#endif /* __linux__ */
