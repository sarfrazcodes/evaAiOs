# Phase 4: Safe Computer Control

## Scope

Phase 4 adds a narrow, allowlisted computer-control boundary. Requests are still classified by the intent engine, then executed through the existing `TaskStep -> Executor -> PermissionHook -> ToolRegistry` path.

Supported actions:

- Launch `google-chrome`, `firefox`, `brave-browser`, `code`, `gnome-calculator`,
	`gnome-text-editor`, or `gnome-control-center` when installed.
- Check whether an allowlisted application is installed.
- Open the user's home directory, `~/Downloads`, or the approved project root
	through `xdg-open`.
- Read, set, mute, and unmute the default audio sink through `wpctl`.

Application launches use fixed executable argument lists. Directory paths are resolved and must remain below an approved root. No user text is passed to a shell.

## Safety Boundary

`PermissionHook` denies unknown tools, unsupported operations, shell metacharacters, and destructive patterns such as `sudo`, `rm -rf`, shutdown, reboot, and poweroff. Volume values are validated from 0 through 100 before execution. Arbitrary shell execution, keyboard or mouse automation, power controls, partitioning, bulk deletion, screenshots, and network automation are not implemented.

Confirmation-required file and audio mutations are persisted as exact task-step
bindings with expiring, one-time confirmation IDs. The API exposes retrieval,
approval, and denial endpoints, and the Flutter task card presents the exact
tool, operation, and target before approval. Actions outside the allowlist are
denied rather than silently approved.

Approval is bound to the original task, step, tool, and canonical arguments;
it expires, can be consumed once, and is revalidated by the executor.

## Reused Components and Files


## Validation

- Baseline before Phase 4 edits: `96 passed`.
- Focused tool, executor, and security tests: `39 passed` before audio-control additions.
- Focused routing and integration tests: `53 passed` before audio-control additions.
- Full suite after implementation: `112 passed`, 3 existing deprecation warnings.

## Environment

The development host is Ubuntu GNOME on Wayland. Chrome, Firefox, VS Code,
Brave, GNOME Calculator, GNOME Text Editor, GNOME Control Center, Nautilus,
`xdg-open`, and `wpctl` are available. The implementation uses absolute
standard-path resolution because the observed backend environment had a broken
`PATH` value.

## Manual Validation

The live backend logs verified `open firefox`, `open downloads folder`, and the
VS Code new-window request through the executor. The environment also verified
the required binaries. Volume mutation was not performed manually; it is
covered with mocked subprocess tests. Silence detection worked, but an audio
capture containing no recognized speech correctly returned HTTP 422.

## Verdict

NOT READY FOR PHASE 5. The safe allowlisted control foundation and interactive
confirmation transport are implemented. Application closing, screenshot/lock
controls, and broader manual validation remain out of scope.