"""
LogVault Python SDK
Audit-Log-as-a-Service client library
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="logvault",
    version="0.2.5",
    author="LogVault",
    author_email="support@logvault.eu",
    description="Audit-Log-as-a-Service client library",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Rul1an/LogVault",
    project_urls={
        "Bug Tracker": "https://github.com/Rul1an/LogVault/issues",
        "Documentation": "https://logvault.eu/docs",
        "Source Code": "https://github.com/Rul1an/LogVault",
    },
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Logging",
        "Topic :: Security",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.31.0",
        "aiohttp>=3.9.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "mypy>=1.0.0",
        ],
    },
    keywords="audit logging compliance soc2 gdpr iso27001 security",
    license="MIT",
)
