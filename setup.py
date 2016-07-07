from setuptools import setup, find_packages

def parse_requirements(filename):
    """ load requirements from a pip requirements file """
    lineiter = (line.strip() for line in open(filename))
    return [line for line in lineiter if line and not line.startswith("#")]

setup(
    name="nagios-mesos",
    description="A selection of Nagios plugins to monitor Apache Mesos.",
    long_description=open('README.rst').read(),
    version="0.2.6",
    packages=find_packages(),
    author='Steven Schlansker',
    author_email='sschlansker@opentable.com',
    url="https://github.com/opentable/nagios-mesos",
    scripts=["check_mesos.py"],
    license="Apache 2",
    install_requires=parse_requirements("requirements.txt"),
    include_package_data=True,
    classifiers=[
      'Development Status :: 4 - Beta',
      'Environment :: Console',
      'Intended Audience :: System Administrators',
      'License :: OSI Approved :: Apache Software License',
      'Topic :: System :: Monitoring',
      'Topic :: System :: Networking :: Monitoring'
    ]
)
