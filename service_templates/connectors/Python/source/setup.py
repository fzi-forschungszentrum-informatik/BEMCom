from setuptools import setup

setup(
    name="pyconnector_template",
    version="0.0.1",
    install_requires=["python-dotenv==0.15.*", "paho-mqtt==1.5.*"],
    packages=setuptools.find_packages(),
)
