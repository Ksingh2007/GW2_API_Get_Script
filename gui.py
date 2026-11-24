"""
GUI front end for GW2 data downloader
"""

import os
import queue
import subprocess
import sys
import threading
import time
import traceback

from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter import font as tkfont
from tkinter.scrolledtext import ScrolledText

import script

LANGUAGES = {
    "en": "English",
    "de": "German",
    "es": "Spanish",
    "fr": "French",
    "zh": "Chinese",
}