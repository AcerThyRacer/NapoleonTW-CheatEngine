## 2024-05-24 - [Fix Path Traversal in Pack Extraction]
**Vulnerability:** A Zip Slip (Path Traversal) vulnerability in `src/pack/pack_parser.py` allowed an attacker to craft a malicious `.pack` archive with files like `../../evil.txt`, which would be extracted outside of the designated output directory.
**Learning:** Archive extractors must validate that extracted files stay within the target directory. `Path(output_path / file_path)` alone is insufficient as `file_path` can contain parent directory traversal (`../`) or absolute paths.
**Prevention:** Always use `Path.resolve()` to get the absolute path and verify `dest_path.relative_to(output_path)` to ensure the destination remains inside the expected output directory.
