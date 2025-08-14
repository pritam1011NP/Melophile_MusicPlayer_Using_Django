# Melophile

A Python utility for parsing and processing LRC (lyrics) files with Django integration.

## Features

- Parse LRC files and extract lyrics data
- Process and analyze lyrics content
- Django integration for web-based lyrics management
- Error handling for malformed LRC files
- Support for various LRC file formats

## Requirements

- Python 3.6+
- Django 3.0+

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/lrc-parser.git
cd lrc-parser
```

2. Install required dependencies:
```bash
pip install django
```

3. Set up Django (if not already configured):
```bash
python manage.py migrate
```

## Usage

### Basic Usage

```python
from test import process_lrc_file

# Process an LRC file
result = process_lrc_file('path/to/your/lyrics.lrc')
print(result)
```

### Django Integration

The project includes Django integration for web-based lyrics processing. Run the development server:

```bash
python manage.py runserver
```

## File Structure

```
.
├── test.py              # Main LRC processing script
├── manage.py           # Django management script
├── requirements.txt    # Project dependencies
└── README.md          # This file
```

## LRC File Format

LRC files follow this format:
```
[00:12.00]Line of lyrics
[00:17.20]Another line of lyrics
[00:21.10]More lyrics here
```

## Common Issues

### F-string Backslash Error

If you encounter this error:
```
SyntaxError: f-string expression part cannot include a backslash
```

This happens when using backslashes (like `\n`) directly in f-string expressions. Use one of these solutions:

```python
# Solution 1: Use a variable
lines_count = len(lrc_data.split('\n')) - 5
print(f"   ... and {lines_count} more lines")

# Solution 2: Use splitlines() method
print(f"   ... and {len(lrc_data.splitlines())-5} more lines")
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Thanks to the LRC format specification community
- Django framework for web integration capabilities

## Contact

Your Name - your.email@example.com

Project Link: [https://github.com/yourusername/lrc-parser](https://github.com/yourusername/lrc-parser)
