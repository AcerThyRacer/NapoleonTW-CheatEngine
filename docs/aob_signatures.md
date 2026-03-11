# Napoleon Total War (v1.6) AOB Signatures

This document outlines the known Array of Bytes (AOB) signatures for critical game instructions in Napoleon Total War v1.6 (32-bit WARSCAPE engine).

These signatures are used to find code locations dynamically, allowing cheats to survive game restarts and updates that might shift memory addresses.

## 1. Treasury Write Instruction (Campaign Gold)
- **Description**: The instruction that writes the updated gold value to the player's faction treasury after spending or earning.
- **Pattern**: `89 86 ?? ?? ?? ?? 8B 45 FC`
- **Assembly**: `MOV [ESI+offset], EAX` followed by `MOV EAX, [EBP-04]`
- **Cheat Action**: NOP this instruction (6 bytes) to prevent the game from updating the gold value, effectively freezing the current treasury.

## 2. Movement Points Write
- **Description**: The instruction that updates an army's remaining movement points on the campaign map.
- **Pattern**: `F3 0F 11 86 ?? ?? ?? ?? F3 0F 10 45`
- **Assembly**: `MOVSS [ESI+offset], XMM0`
- **Cheat Action**: NOP this instruction (8 bytes) to prevent the game from decrementing movement points when armies move, granting unlimited movement.

## 3. Unit Health Write (Battle)
- **Description**: The instruction that writes the updated health value for a unit during a battle after taking damage.
- **Pattern**: `F3 0F 11 ?? ?? ?? ?? ?? 8B ?? ?? ?? ?? ?? 85`
- **Assembly**: `MOVSS [reg+offset], XMMn`
- **Cheat Action**: NOP this instruction (8 bytes) to prevent the health value from decreasing, granting the unit god mode.

## 4. Ammo Decrement Instruction
- **Description**: The instruction that decrements the remaining ammunition count for a ranged unit when it fires.
- **Pattern**: `29 ?? ?? ?? ?? ?? 89 ?? ?? ?? ?? ?? 83`
- **Assembly**: `SUB [reg+offset], reg`
- **Cheat Action**: NOP this instruction (6 bytes) to prevent ammo from being consumed during a battle.
