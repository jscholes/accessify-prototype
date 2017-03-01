from setuptools import setup


setup(
    name='Accessify',
    version='0.1',
    url='https://github.com/jscholes/accessify',
    author='James Scholes',
    description='Accessible control interface for Spotify on Windows',
    packages=['accessify'],
    entry_points={
        'console_scripts':[
            'accessify = accessify.main:main'
        ]
    }
)
