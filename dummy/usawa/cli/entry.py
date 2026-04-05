import uuid
import datetime
import logging
import sys
import tempfile
import subprocess
import mimetypes

from usawa import Asset, Entry, EntryPart
from usawa.account import Account, AccountDisplay, AccountType
from usawa.balance import Balancer

logg = logging.getLogger('cli.entry')

class AbortMenu(Exception):
    pass


def writehelp(w=sys.stdout):
    s = """h: this help
i: input account
o: output account
y: ref
x: extref
r: reset accounts
d: description
+: add tag
-: remove tag
v: view matched attachment (in any)
s: skip entry
t: save entry to draft
w: write entry
q: quit
"""
    w.write(s + "\n")



def choose_account(ctx, include_create=False):
    r = None
    accounts_r = []
    while not r:
        a = None
        if len(accounts_r) == 0:
            a = input('enter account: ')
            if a == 'q':
                raise AbortMenu()
        elif len(accounts_r) == 1:
            r = accounts_r[0]
            break
        else:
            v = input('choose match: ')
            i = None
            if v == 'q':
                raise AbortMenu()
            try:
               i = int(v)
            except ValueError:
                logg.debug('Invalid number, going back to search')
                a = v

            if i != None:
                try:
                    r = accounts_r[i]
                except IndexError:
                    logg.error('Number out of range')
                continue
        accounts_r = []
        ctx.aidx.set_filter(path=a)
        i = 0
        for a in ctx.aidx:
            accounts_r.append(a)
            print('{} {}'.format(i, a))
            i += 1
        if i == 0:
            logg.debug('no accounts found')
        ctx.aidx.reset_filter()
    return r


def parse_unit(ctx, v):
    return ctx.uidx.sym(v)


def parse_amount(ctx, sym, v):
    return ctx.uidx.from_floatstring(sym, v)


def parse_side(ctx, v):
    for k in ['src', 'dst']:
        if k.startswith(v):
            return k
    raise ValueError('invalid side: ' + v)


def parse_txdate(ctx, v):
    return datetime.date.fromisoformat(v)


def input_or_default(prompt, default=None, postfix=': ', validate_fn=None):
    if default != None:
        postfix = ' [{}]'.format(default) + postfix
    v = input(prompt + postfix)
    if len(v) == 0:
        if default == None:
            raise ValueError('empty value and no default')
        v = default
    if validate_fn != None:
        validate_fn(v)
    return v


def handle_tag(ctx, entry, v):
    r = input('Tag: ')
    if v == '+':
        entry.tag(r)
    elif v == '-':
        entry.untag(r)


def handle_view(ctx, entry, o):
    if len(entry.attachment) == 0:
        logg.error('no asset to resolve')
        return
    if ctx.resolver == None:
        logg.error('no resolver to provide view')
        return
    asset = entry.attachment[0]
    ext = mimetypes.guess_extension(asset.mime)
    (f, fp) = tempfile.mkstemp(suffix=ext)
    k = asset.get_digest()
    asset_data = ctx.resolver.get(k)
    f = open(fp, 'wb')
    f.write(asset_data)
    f.close()
    subprocess.Popen(
            ['xdg-open', fp],
            stderr=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            )


def handle_description(ctx, entry, v, prefix=None):
    v = input_or_default("description", entry.description)
    entry.description = v


def handle_reset(ctx, entry, v):
    entry.debit = []
    entry.credit = []
    entry.balancer = Balancer(self.ctx.uidx)


def handle_ref(ctx, entry, v):
    ref = None
    label = 'ref'
    if v == 'y':
        ref = entry.ref
    else:
        ref = entry.extref
        label = 'ext' + label
    v = input_or_default(label, ref)
    if v == 'y':
        entry.ref = v
    else:
        entry.extref = v


def try_entry_uuid(ctx, v):
    v = uuid.UUID(v)
    entry = Entry.empty(ref=str(v))
    return ctx.store.get_draft(entry, unitindex=ctx.uidx)


def try_entry_serial(ctx, v):
    v = int(v)
    entry = Entry(v, None)
    return ctx.store.get_entry(entry)


def try_entry_digest(ctx, k):
    if isinstance(k, str):
        k = bytes.fromhex(k)
    if len(k) != 64:
        raise ValueError('invalid digest length')
    v = ctx.resolver.get(k)
    return Entry.from_string(v, ctx.uidx)


def try_entry(ctx, entry_spec):
    if not entry_spec:
        return Entry.empty(unitindex=ctx.uidx)

    try:
        return try_entry_serial(ctx, entry_spec)
    except ValueError:
        pass

    try:
        v = try_entry_uuid(ctx, entry_spec)
        if v == None:
            raise AttributeError('entry is committed')
        return v
    except ValueError:
        pass
    except FileNotFoundError:
        pass

    try:
        return try_entry_digest(ctx, entry_spec)
    except ValueError:
        pass

    return None


class EntrySession:

    def __init__(self, ctx, entry=None, heading=None, description=None, extref=None, dt=None, ref=None, amount=None, lines=[], base=None):
        # context props
        self.ctx = ctx
        self.unitbase = base
        if self.unitbase == None:
            self.unitbase = self.ctx.uidx.base

        # override props
        self.description = description
        self.ref = ref
        self.extref = extref
        self.dt = dt

        # state props
        self.commit = False
        self.final = False
        self.part_side = 'src'
        self.have_src = False
        self.have_dst = False

        # supplementary props
        self.heading = heading
        self.lines = lines
        self.amount = float(amount)

        self.entry = try_entry(self.ctx, entry)
        if self.entry == None:
            self.entry = Entry.empty(unitindex=self.ctx.uidx, description=self.description, ref=self.ref, extref=self.extref, tx_date=self.dt)
        if self.entry.serial > 0:
            raise NotImplementedError('entry edit not yet implemented')
        self._do_prepare()


    def _cur_amount(self):
        amount = self.ctx.uidx.val(self.unitbase, self.amount)
        if amount == None:
            amount = self.entry.balancer.value()
        else:
            amount = amount[0]
        return amount


    def _src_remaining(self):
        amount = self._cur_amount()
        return amount - self.entry.balancer.src()


    def _dst_remaining(self):
        amount = self._cur_amount()
        return amount - self.entry.balancer.dst()


    def _do_prepare(self):
        uu = uuid.uuid4()
        self.ref = str(uu)
        dt = datetime.datetime.now(datetime.UTC)
        self.dt = dt


    def attach_ref(self, v):
        k = uuid.UUID(v) 
        asset = Asset(ref=str(k))
        asset = self.ctx.store.get_asset_indexed(asset)
        self.entry.attach(asset)


    def attach_digest(self, v):
        k = bytes.fromhex(v)
        asset = Asset(digest=k)
        asset = self.ctx.store.get_asset(asset)
        self.entry.attach(asset)


    def enter_part(self, side=None):
        if side != None:
            self.part_side = side
        elif len(self.entry.debit) > 0:
            if self.have_dst:
                self.part_side = 'dst'
            else:
                self.part_side = 'src'
            v = input_or_default('Entry side', self.part_side)
            if v == '':
                return False
            k = parse_side(ctx, v)
            self.part_side = k

        #v = input_or_default('Entry {} account'.format(ctx.get('partk')))
        #account = parse_account(ctx, v, sym=unit, typ=typ)
        try:
            v = choose_account(self.ctx)
        except AbortMenu:
            return False
        account = Account.from_path(v)

        #amount = None
        rem = 0
        if self.part_side == 'src':
            rem = self._src_remaining()
        else:
            rem = self._dst_remaining()
        rem = self.ctx.uidx.to_floatstring(account.sym, rem)
        v = input_or_default('Account {} amount'.format(account), rem)
        amount = parse_amount(self.ctx, account.sym, v)

        isdebit = self.part_side=='src'
        part = EntryPart(account.sym, account.typ.value.lower(), account.to_path(display=AccountDisplay.path), amount, debit=isdebit)
        self.entry.add_part(part)

        if self.part_side == 'src':
            self.have_src = True

        if self.part_side == 'dst':
            self.have_dst = True

        return True


    def handle_input(self, v):
        if v == 'i' or v == 'o':
            k = 'src'
            if v == 'o':
                k = 'dst' 
            self.enter_part(side=k)
            return True
        if v == 'q':
            raise StopIteration()
        if v == '+' or v == '-':
            r = handle_tag(self.ctx, self.entry, v)
            return True
        if v == 'w':
            self.commit = True
            self.final = True
            return False
        if v == 't':
            self.commit = True
            return False
        if v == 'v':
            handle_view(self.ctx, self.entry, v)
            return True
        if v == 'x' or v == 'y':
            handle_ref(self.ctx, self.entry, v)
            return True
        if v == 'd':
            handle_description(self.ctx, self.entry, v, prefix=self.heading)
            return True
        if v == 'r':
            handle_reset(self.ctx, self.entry, v)
            return True
        if v == 's':
            return False
        logg.error('invalid input')
        return True


    def do_interactive_one(self):
        v = input_or_default('Entry description', self.entry.description)
        self.entry.description = v
        v = input_or_default('External ref', self.entry.ref)
        self.entry.ref = v
        v = input_or_default('Transaction date(time)', self.entry.dt)
        if isinstance(v, str):
            v = parse_txdate(self.ctx, v)
        self.entry.dt = v


    def do_interactive_two(self, w=sys.stdout):
        r = True
        while r:
            w.write(str(self) + "\n")
            v = input("> ")
            r = self.handle_input(v)


    def check(self):
        if self.entry.description == None:
            raise ValueError('missing description')

    """
    :return: True to continue edit entry, false to end entry
    """
    def finalize(self):
        if not self.commit:
            logg.debug('skipping ' + str(self.entry))
            return False

        v = input('write: are you sure? (YES)')
        if v != 'YES':
            logg.debug('abort write ' + str(self.entry))
            return True

        try:
            self.check()
        except Exception as e:
            logg.error('abort write on check error: ' + str(e))

        if self.final:
            self.entry.description = self.get_description()
            self.entry.parent = self.ctx.ledger.cur
            self.entry.serial = self.ctx.ledger.next_serial()
            self.entry.sign(self.ctx.wallet)
            self.ctx.store.add_entry(self.entry, update_ledger=True)
            self.ctx.store.put_draft(self.entry)
            self.ctx.ledger.truncate()
            self.ctx.ledger.sign()
            f = open(self.ctx.ledger_path_out, 'w')
            f.write(self.ctx.ledger.to_string())
            f.close()
            if self.ctx.resolver != None:
                self.ctx.resolver.put_entry(self.entry, lookup='sha512')
        else:
            self.ctx.store.put_draft(self.entry)

        return False


    def start(self, skip_first=False):
        if not skip_first:
            self.do_interactive_one()
        r = True
        while r:
            try:
                self.do_interactive_two()
            except StopIteration:
                return None
            r = self.finalize()
        return self.entry


    def get_description(self):
        description = self.entry.description
        if self.heading != None:
            description = self.heading + "; " + description
        return description


    def __str__(self):
        s = """Date: {}
Ref: {}
Extref: {}
""".format(
        self.entry.dt,
        self.entry.ref,
        self.entry.extref,
        )

        s += "Description: " + self.get_description() + "\n"

        for v in self.lines:
            s += "\t" + v + "\n"

        amount = self._cur_amount()
        amount = self.ctx.uidx.to_floatstring(self.unitbase, amount)
        rem = self._src_remaining()
        rem = self.ctx.uidx.to_floatstring(self.unitbase, rem)
        s += "Accounts src: {}/{}\n".format(rem, amount)
        for v in self.entry.debit:
            typ = getattr(AccountType, v.typ)
            o = Account.from_path(v.account, sym=v.unit, typ=typ)
            s += "\t" + o.to_path() + " " + self.ctx.uidx.to_floatstring(v.unit, v.amount) + "\n"

        rem = self._dst_remaining()
        rem = self.ctx.uidx.to_floatstring(self.unitbase, rem)
        s += "Accounts dst: {}/{}\n".format(rem, amount)
        for v in self.entry.credit:
            typ = getattr(AccountType, v.typ)
            o = Account.from_path(v.account, sym=v.unit, typ=typ)
            s += "\t" + o.to_path() + " " + self.ctx.uidx.to_floatstring(v.unit, v.amount) + "\n"

        return s
