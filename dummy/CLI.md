# Tutorial - usawa CLI

All commands has a debug option on the `-v` flag. Valid values are `debug`, `info`, `warning` and `error`. Default is `warning`

Some commands prompt for passphrases. If an empty passphrase is given on wallet creation (i.e. just pressed "enter"), the `-p` flag is not necessary for consecutive commands.


## Preparations

### Accounts list

Accounts are ordered by units of account, account type and account path respectively.

There are five account types:

- Asset
- Liability
- Income
- Expense
- Equity

At this time, valid accounts are listed in a separate file, specifically mentioned by the configuration below. Although it is possible to use any account path with


### Configuration

For this tutorial, we will use the fs backend for localstore and asset resolver. This means each entry and asset will be stored as individual files under a directory.

We create a configuration override to specify the fs backend:

```
configdir=$(realpath ./fsconfig)
storedir=$(realpath ./fsstore)
objdir=$(realpath ./fsobj)
mkdir -vp $configdir $storedir $objdir
cat <<EOF > $configdir/config.ini
[store]
type = fs
[fsstore]
base = $storedir
[fs_resolver]
store_path = $objdir
EOF

```


## Creating signing key

To maintain ledgers and ledger entries, a signing key is required.

To create it:

```
# will prompt for a passphrase.
# creates new default key in the fs store
usawa-wallet -c fsconfig
```


## Create new ledger

This will use the default key in the store.

```
# topic is an arbitrary value.
# units of account for the ledger are specified 
usawa-create -c fsconfig -t myledger -u USD:2 -u BTC:9 -u EUR:2 -p > state.xml
```

### Back up the initial ledger

The ledger first created has serial 0 and zero-value hash parent. This ledger state may be used later for example for commands listing transactions.

```
cp state.xml init.xml
```


## Create a new ledger entry

This is an interactive tool, where a single ledger entry can be added to the ledger.

```
usawa-entry -c fsconfig -i init.xml
```

### Entering data

For a new entry it will prompt for some information:

* Entry description (free text)
* Internal ref (a uuid string)
* External ref (optional)
* Date (and optionally time) of transaction.

After this phase, an interactive menu is presented. Menu options are single character strings. To see all available options in the menu, write `h`

The primary action in the interactive phase is to enter transaction deltas on each side of the ledger. `i` lets you add a "source" (or debit) account, `o` lets you add a "destination" (or credit) account. Each entry may have one or more transaction deltas.

**NOTE! The CLI tool will NOT enforce zero-sum between debit and credit. Also, the sums/balances displayed per entry do not work correctly yet**


### Storing data

Once the entry has been completed, select `w` to commit the entry to the ledger.

"Commit" means:

* The entry is added to the local store. Any attempt at adding an additional entry with the same serial number to the store will fail.
* The ledger xml file is updated with the new serial number and entry digest, and a signature of the client private key is applied.


## View the ledger entries

To view all entries in a ledger as a single XML document, from oldest to newest (serial numbers, incrementally):

```
usawa-view -c fsconfig -i init.xml
```


## Export entry XML

Extract each entry into individual XML.

```
usawa-export -c fsconfig -i init.xml <target_dir>
```

Two versions will be generated per entry, one canonical *digest* XML that is used for the digest for the entry in the ledger chain.

The other is the canonical *full* XML, containing all other elements not part of the *digest* XML.


## Interpreting the XML

### Ledger

The ledger xml contains the serial number and digest of the last comitted entry.

The consecutive entry will have that digest as it's **parent** value, along with the *following* serial number.


### Entry

The parent digest is the sha512 of the canonical *full* XML.

The signature is calculated over the correspinding canonical *digest* XML.
