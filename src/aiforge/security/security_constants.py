class SecurityConstants:
    DANGEROUS_MODULES = [
        "subprocess",
        "multiprocessing",
        "ctypes",
        "importlib.util",
        "runpy",
        "code",
        "codeop",
    ]

    DANGEROUS_NETWORK_MODULES = [
        "socket",
        "telnetlib",
        "ftplib",
        "smtplib",
        "poplib",
        "imaplib",
    ]

    NETWORK_MODULES = [
        "requests",
        "urllib",
        "http.client",
    ]

    DANGEROUS_PATTERNS = [
        # Command Execution
        r"os\.system\(",
        r"os\.exec\w*\(",
        r"os\.spawn\w*\(",
        r"os\.popen\(",
        r"subprocess\.",
        # Dynamic Code Execution
        r"eval\(",
        r"exec\(",
        r"compile\(",
        r"__import__\(",
        r'__import__\([^)]*["\']subprocess["\']',
        # Serialization and Deserialization
        r"pickle\.loads?\(",
        r"shelve\.open\(",
        r"marshal\.loads?\(",
        # File System Operations
        r'open\([^)]*["\']w["\']',  # Potentially dangerous write access
        r"shutil\.rmtree\(",
        r"os\.remove\(",
        r"os\.rmdir\(",
        r"\.unlink\(\)",
        r"\.delete\(\)",
        # Reflection and Attribute Access
        r'getattr\([^)]*["\']system["\']',
    ]

    COMMON_MODULES = {
        "requests": "requests",
        "json": "json",
        "os": "os",
        "re": "re",
        "sys": "sys",
        "time": "time",
        "random": "random",
        "datetime": "datetime",
        "BeautifulSoup": "bs4.BeautifulSoup",
        "pd": "pandas",
        "np": "numpy",
        "plt": "matplotlib.pyplot",
    }
