# -*- mode: python -*-

import glob
import os.path

import tolk


block_cipher = None

data_files = []
tolk_data_files = [(path, '.') for path in glob.glob(os.path.join(os.path.dirname(tolk.__file__), '*.dll'))]
data_files.extend(tolk_data_files)

a = Analysis(['..\\accessify\\main.py'],
             pathex=['build'],
             binaries=[],
             datas=data_files,
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='accessify',
          debug=False,
          strip=False,
          upx=True,
          console=False )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='accessify')
