# Rule: How AI Agents Work in This Repository

Applies to every agent (Claude, Codex, Gemini, Copilot, Cursor and others).

1. **Plan first for new modules.** Before writing code:
   - restate the spec
   - read the files it touches
   - list the patterns you will copy, with file paths
   - state the decisions you made where the spec is open, and the risks

   Then wait for the owner's approval.
2. **One branch.** Work on the branch you are given. Do not create branches, commit, push or open pull requests unless asked.
3. **Copy, do not invent.** Follow the reference modules in [docs/ENGINEERING_PLAYBOOK.md](../../docs/ENGINEERING_PLAYBOOK.md). Match the surrounding code's naming, comment density and layout.
4. **Enforce what you build.** A rule that is stored but not checked must be called out in the UI and in `docs/SECURITY.md`.
5. **Verify before you report:**
   - run `./scripts/validate_structures.sh`
   - for access or security changes, run a live check against the running API with temporary, tagged data, and delete it afterwards
   - for UI changes, look at the page at 1440px and 375px
6. **Report honestly.** Say what was tested and how, what failed, and what is not done. Never describe unrun checks as passing.
7. **Credentials.**
   - Use test values only for local checks.
   - Never type, store or repeat a real password, including one visible in a screenshot or file.
   - Remove any test sign-in you set up.
8. **Commits, when asked:**
   - run `./scripts/bump_version.sh [patch|minor|major]` first
   - use the history's message format: `feat(scope): add <thing>, ADM-XXX (vX.Y.Z, build N)`
   - follow your tool's attribution rules
9. **Docs travel with code.** Update `docs/SECURITY.md`, `docs/PHASE.md` and, when setup changes, `README.md` in the same change.
