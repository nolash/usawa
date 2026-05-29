import os

from setuptools import setup

script_dir = os.path.realpath(os.path.dirname(__file__))
aux_dir = os.path.join(script_dir, 'aux')
varints_dir = os.path.join(aux_dir, 'varints', 'varints')


setup(
        install_requires=[
            "filemagic~=1.6",
            "wheepy[valkey,fs]~=0.0.7a1",
            "confini~=0.6.5",
            "lxml~=6.0.2",
            "PyNaCl~=1.6.0",
            "rencode==1.0.6",
            "hexathon~=0.1.7",
            "xdg-base-dirs~=6.0.2",
            "varints@file://" + varints_dir,
            ],
        extras_require={
            'gui': [
                "PyGObject~=3.52.3",
                ],
            }
        )
