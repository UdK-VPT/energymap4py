from setuptools import setup, find_packages

setup(
    name='energymap4py',
    version='0.42.0',
    packages=find_packages(),
    install_requires=[
        "requests"
    ],
    author='Alexander Küster-Inderfurth, a.inderfurth@udk-berlin.de',
    description='energymap4py provides access to the EnergyMap Berlin database and AI prognosis model.',
    url='https://github.com/UdK-VPT/energymap4py',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: BSD 3',
    ],
)
