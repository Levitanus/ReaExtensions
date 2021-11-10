from distutils.core import setup

setup(
    name='rea_extensions',
    version='0.1',
    description='Number of small tools for everyday reaper usage',
    author='Levitanus',
    author_email='pianoist@ya.ru',
    # entry_points={
    #     'console_scripts': ['sample_editor = sample_editor.__main__:main']
    # },
    packages=['rea_extensions'],  # same as name
    package_data={'rea_extensions': ['py.typed']},
    install_requires=['python-reapy'],
)
