# HATUI

BlackRainLabs Hybrid Active Directory Terminal UI — a dark-chrome console for identity, directory, Exchange, and Entra administration in a hybrid environment.

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
hatui
```

Default mode is an in-memory **BlackRainLabs** hybrid forest (`blackrainlabs.corp`). No credentials required.

```
hatui                  # mock mode (hatui.toml)
hatui --mode mock
hatui --config ./hatui.toml
```

## Keys

| Key | Action |
|-----|--------|
| `F1` | Help |
| `/` | Filter current list |
| `a` / double-click row | Actions for selection |
| `Enter` | Same as double-click row |
| `n` | New object |
| `:` | Jump to module |
| `Ctrl+L` | Sign in (LDAP + Graph login) |
| `Ctrl+P` | Command palette |
| `q` | Quit |

## Live connectors

Set `mode = "live"` in `hatui.toml` and enable LDAP / Graph. **Login is the default** (`auth = "login"`): the operator signs in with a UPN and password. `Ctrl+L` opens the sign-in modal.

```
HATUI_USERNAME=admin@blackrainlabs.corp
HATUI_PASSWORD=...
hatui --mode live
```

Adapter-specific overrides:

- `HATUI_LDAP_USERNAME` / `HATUI_LDAP_PASSWORD` — LDAP user bind (UPN or `DOMAIN\\sAM`)
- `HATUI_GRAPH_USERNAME` / `HATUI_GRAPH_PASSWORD` — Microsoft Graph resource-owner password grant
- `HATUI_GRAPH_CLIENT_SECRET` — only when Graph `auth = "client_credentials"`

LDAP `auth = "bind"` still accepts a service `bind_dn`. Graph login uses a public (or confidential) app registration that allows ROPC.

Unconfigured connectors stay dark on the status bar; mock remains the default.
