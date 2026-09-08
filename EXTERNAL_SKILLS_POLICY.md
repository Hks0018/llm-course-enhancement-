# External Skills Policy

`skills/registry.json` currently lists 24 skills, all `"source": "internal"`. This
is deliberate, not an oversight - the engine ships fully self-contained.

If an external skill (from skills.sh or elsewhere) is ever considered as a
replacement for, or addition to, one of these, check all seven of the following
**before** adding it to the registry:

1. **Purpose** - does it do the same job as the internal skill it would
   replace/supplement, or something adjacent that would change the engine's
   behavior?
2. **License** - is it under a license compatible with this project's use
   (no viral copyleft that would force relicensing the engine, no
   field-of-use restrictions)?
3. **Free / open-source** - is the skill itself free to use? (Not just "has a free
   tier" - a metered/paid API embedded in a "skill" is a paid dependency, see #4.)
4. **Paid dependencies** - does it call out to a paid API or service at runtime? If
   so, the engine silently starts costing money per course processed, which nothing
   in the current architecture assumes or budgets for.
5. **Architectural compatibility** - does it accept/return data compatible with
   `schema.py`'s normalized course shape, or the specific enhancement-type schemas
   in this codebase, without requiring the core engine to bend around it?
6. **LMS independence** - critically: does the skill assume or hard-code Odoo (or
   any other specific LMS)? If yes, it belongs in an *adapter*, not in `skills/` -
   see the architecture rule in [README.md](README.md).
7. **Prefer internal** - if steps 1-6 don't reveal a clear, meaningful advantage
   over writing (or improving) a native internal skill, don't add the external
   dependency. An internal implementation is auditable, has no license risk, no
   runtime cost, and can't disappear out from under the engine.

## Registering one that passes

Add an entry to `skills/registry.json`:

```json
{"skill": "<kebab-case-name>", "source": "external:<provider>", "enabled": true, "dependencies": [...]}
```

Do not set `"enabled": true` for anything that hasn't been checked against all
seven points above. Document the check (which points passed, and why) in the pull
request or commit that adds it - future maintainers need to see the reasoning, not
just the conclusion.
