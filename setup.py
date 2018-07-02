from setuptools import setup

setup(
    name='ictv-plugin-survey',
    version='0.1',
    packages=['ictv.plugins.survey', 'ictv.renderer'],
    package_dir={'ictv': 'ictv'},
    url='https://github.com/OpenWeek/ictv-plugin-survey',
    license='MIT',
    author='Arnaud Gellens, Arthur van Stratum, Céline Deknop, Charles-Henry Bertrand Van Ouytsel, Margerie Huet, Simon Gustin',
    author_email='',
    description='survey is a simple plugin to conduct surveys inside ICTV.',
    include_package_data=True,
)
