# Copilot Instructions

## Terminal & Shell Output
- **NO LARGE HEREDOCS:** When providing shell commands to create or overwrite files, **avoid** using `cat << 'EOF'` or other heredoc patterns for content longer than 10 lines.
  - **Reason:** Large heredocs frequently cause terminal buffers to hang or truncate the input, leaving the shell in a broken state.
  - **Alternative:** Use `printf` for small files. For larger files, write a small Python one-liner (e.g., `python3 -c 'print("... long content ...")' > file`) or instruct the user to create the file manually.
- **Verification:** Always ensure shell commands are syntactically complete and safe to paste.
