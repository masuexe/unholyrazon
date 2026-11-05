#!/usr/bin/env python3
"""Compile the actual daily-FF ACS policy under C stubs and exercise its contracts."""
from pathlib import Path
import json
import re
import subprocess
import tempfile
import gen_daily_ff_data

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / 'src/acs_source/classes/shared/copy_weapons/daily_team_ff.acs'


def main():
    generated = gen_daily_ff_data.render()
    if gen_daily_ff_data.OUTPUT.read_text() != generated:
        raise SystemExit('Daily FF data is stale')
    registry = (ROOT / 'src/acs_source/classes/shared/copy_weapons/copy_weapon_registration.acs').read_text()
    lists = {}
    for kind in ('QWANT', 'NEGA'):
        lists[kind] = re.findall(r'DefineCopyWep\(UHCOPY_' + kind + r',\s*\w+,\s*"([^"]+)"', registry)
    definitions = (ROOT / 'src/acs_source/classes/survivors/definitions/uh_survdefs.acs').read_text()
    survivors = dict((int(i), actor) for i, actor in re.findall(r'DefineSurvivor\((\d+),\s*"([^"]+)"', definitions))
    decoy_source = (ROOT / 'src/acs_source/classes/shared/copy_weapons/decoy_defs.acs').read_text()
    decoys = re.findall(r'DefineDecoyBotMoveWep\("([^"]+)"', decoy_source)
    decoys = [s[:-2] if s.endswith('_W') else s for s in decoys]
    header = (ROOT / 'tools/fixtures/daily_ff_stubs.c').read_text()
    for name, values in [('qw', lists['QWANT']), ('ng', lists['NEGA'])]:
        header += 'str ' + name + '[] = {' + ','.join(map(json.dumps, values)) + '};\n'
    header += 'str survivors[128] = {' + ','.join('[' + str(i) + ']=' + json.dumps(a) for i, a in survivors.items()) + '};\n'
    header += 'str uh_decoymovewep[256][3] = {' + ','.join('{' + json.dumps(s) + ',"",""}' for s in decoys) + '};\n'
    header += f'int CountDecoyBotSlots(void) {{return {len(decoys)};}}\n'
    header += f'int CountCopyWepByKind(int kind) {{return kind == 2 ? {len(lists["QWANT"])} : {len(lists["NEGA"])};}}\n'
    source = POLICY.read_text().split('script "uh_debug_ShowDailyTeamFF"')[0]
    source = source.replace('#include "daily_ff_data.acs"', generated)
    source = source.replace('#include "uh_teamff_defs.acs"', (ROOT / 'src/acs_source/_includes/mod_api/uh_teamff_defs.acs').read_text())
    source = source.replace('function ', '')
    source = re.sub(r'script "(\w+)"\s*\(([^)]*)\)(?: EVENT)?', r'void \1(\2)', source)
    source = source.replace('int attack)', 'str attack)').replace('int dtype)', 'str dtype)').replace('int actor)', 'str actor)')
    source = re.sub(r'\bterminate\s*;', 'return;', source)
    source = source.replace('StrParam(s:"DecoyCopy_", c:GetChar(actor, 8), c:GetChar(actor, 9))', 'decoy_name(actor)')
    trailer = (ROOT / 'tools/fixtures/daily_ff_cases.c').read_text()
    with tempfile.TemporaryDirectory(prefix='uh-daily-ff-') as scratch:
        c = Path(scratch) / 'policy.c'
        binary = Path(scratch) / 'policy'
        c.write_text(header + source + trailer)
        subprocess.run(['cc', '-std=c99', '-fwrapv', '-Werror=implicit-function-declaration', str(c), '-o', str(binary)], check=True)
        subprocess.run([str(binary)], check=True)


if __name__ == '__main__':
    main()
