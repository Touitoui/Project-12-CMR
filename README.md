# Project-12-CMR

Epic Events CRM - Customer Relationship Management System with JWT Authentication

## Features

- ✅ User authentication with JWT (JSON Web Tokens)
- ✅ Persistent authentication using local token storage
- ✅ Password hashing with Argon2
- ✅ MVC architecture (Model-View-Controller)
- ✅ Department-based authorization (Commercial, Support, Gestion)

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up your database and create a sample user:
```bash
python create_sample_user.py
```

## Usage

Commands follow the pattern:

```
python epicevents.py <group> <command>
```

You must be logged in before running any command other than `auth login`.

### Discovering commands

Use `--help` at any level to see available options:

```
python epicevents.py --help
```
```
Commands:
  auth       Authentication commands.
  clients    Client management commands.
  contracts  Contract management commands.
  events     Event management commands.
  users      User management commands (GESTION role only).
```

```
python epicevents.py <group> --help
```

### auth — Authentication

```
python epicevents.py auth --help
```
```
Commands:
  login   Log in with your credentials.
  logout  Log out the current user.
  whoami  Show the currently logged-in user.
```

| Command | Description |
|---|---|
| `python epicevents.py auth login` | Prompt for email & password, store JWT token locally |
| `python epicevents.py auth logout` | Revoke and delete the stored token |
| `python epicevents.py auth whoami` | Display the currently authenticated user |

### users — User management *(GESTION role only)*

```
python epicevents.py users --help
```
```
Commands:
  create  Create a new user.
  delete  Delete a user.
  list    List all users.
  update  Update an existing user.
```

| Command | Description |
|---|---|
| `python epicevents.py users create` | Create a new user (prompts for details) |
| `python epicevents.py users list` | List all CRM users |
| `python epicevents.py users update` | Update an existing user |
| `python epicevents.py users delete` | Delete a user |

### clients — Client management

```
python epicevents.py clients --help
```
```
Commands:
  create  Create a new client.
  list    List all clients.
  update  Update an existing client.
```

| Command | Description |
|---|---|
| `python epicevents.py clients create` | Create a new client (Commercial only) |
| `python epicevents.py clients list` | List all clients |
| `python epicevents.py clients update` | Update a client's information (assigned Commercial only) |

### contracts — Contract management

```
python epicevents.py contracts --help
```
```
Commands:
  create         Create a new contract.
  list           List all contracts.
  list-unpaid    List contracts with an outstanding balance.
  list-unsigned  List contracts that have not been signed yet.
  sign           Mark a contract as signed.
  update         Update an existing contract.
```

| Command | Description |
|---|---|
| `python epicevents.py contracts create` | Create a new contract (Gestion only) |
| `python epicevents.py contracts list` | List all contracts |
| `python epicevents.py contracts list-unsigned` | Filter: unsigned contracts only |
| `python epicevents.py contracts list-unpaid` | Filter: contracts with remaining balance |
| `python epicevents.py contracts update` | Update a contract |
| `python epicevents.py contracts sign` | Mark a contract as signed |

### events — Event management

```
python epicevents.py events --help
```
```
Commands:
  assign           Assign a support contact to an event.
  create           Create a new event.
  list             List all events.
  list-mine        List events assigned to the current user.
  list-no-support  List events that have no support contact assigned.
  update           Update an existing event.
```

| Command | Description |
|---|---|
| `python epicevents.py events create` | Create a new event (Commercial, on a signed contract) |
| `python epicevents.py events list` | List all events |
| `python epicevents.py events list-no-support` | Filter: events without a support contact (Gestion) |
| `python epicevents.py events list-mine` | Filter: events assigned to the logged-in user (Support) |
| `python epicevents.py events update` | Update an event (assigned Support or Gestion) |
| `python epicevents.py events assign` | Assign a support contact to an event (Gestion only) |