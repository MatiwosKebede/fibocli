from setuptools import setup, find_packages

setup(
    name="learning_ecology_system",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "click",
        "rich",
        "bcrypt"
    ],
    entry_points={
        'console_scripts': [
            'ecology = cli:cli',
        ],
    },
    description="Hierarchical Learning Ecology System",
    author="Your Name",
    author_email="your.email@example.com",
)
