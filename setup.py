from setuptools import setup, find_packages
import io

setup(
    name="productivity-assistant",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "python-dateutil>=2.8.2",
        "rich>=13.7.0",
        "typer>=0.9.0",
        "pydantic>=2.6.1",
        "openai>=1.12.0",
        "python-dotenv>=1.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=8.0.0",
            "black>=24.1.1",
            "isort>=5.13.2",
            "mypy>=1.8.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "roy=src.main:app",
        ],
    },
    author="Your Name",
    author_email="your.email@example.com",
    description="A terminal-based productivity assistant with GTD-style workflow",
    long_description=io.open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/productivity-assistant",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
) 