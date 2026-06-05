# llm-extract

Extract structured data from text files using large language models. You define the attributes you want to extract in a simple CSV file, and `llm-extract` pulls them out for you.

## What it does

Given a text file and a CSV describing the attributes you want, `llm-extract` uses an LLM to read the text and return the values — with the correct types.

**Example text (`sample.txt`):**
```
The Aeron Chair by Herman Miller is a premium ergonomic office chair retailing
at $1,495. It is currently in stock and listed under the Furniture category...
```

**Example attributes (`attributes.csv`):**
```
name,type,description
product_name,str,The name of the product
price,float,The price of the product in USD as a plain decimal number
in_stock,bool,Whether the product is currently available
```

**Run:**
```
llm-extract --file sample.txt --attrs attributes.csv
```

**Output:**
```
name          value
product_name  Aeron Chair by Herman Miller
price         1495.0
in_stock      True
```

---

## Installation

### 1. Install uv

`uv` is a fast Python package manager. If not already installed, install it with one command:

**macOS / Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows** (run in PowerShell):
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Then restart your terminal. For more details or troubleshooting, see the [uv installation docs](https://docs.astral.sh/uv/getting-started/installation/).

### 2. Install llm-extract

```bash
uv tool install git+https://github.com/destiny-evidence/llm-extract
```

This installs `llm-extract` as a command available anywhere on your machine.

### 3. Configure your credentials

`llm-extract` needs access to an LLM. Set the following three environment variables:

| Variable | Description |
|---|---|
| `LLM_EXTRACT_API_BASE` | The URL of your LLM provider (e.g. `https://api.openai.com/v1`) |
| `LLM_EXTRACT_API_KEY` | Your API key |
| `LLM_EXTRACT_MODEL` | The model to use (e.g. `openai/gpt-4o`) |

The easiest way is to create a config file in your home directory:

**macOS / Linux** — create `~/.config/llm-extract/.env`:
```bash
mkdir -p ~/.config/llm-extract
cat > ~/.config/llm-extract/.env << EOF
LLM_EXTRACT_API_BASE=https://api.openai.com/v1
LLM_EXTRACT_API_KEY=your-api-key-here
LLM_EXTRACT_MODEL=openai/gpt-4o
EOF
```

**Windows** — create `%APPDATA%\llm-extract\.env`:
```
LLM_EXTRACT_API_BASE=https://api.openai.com/v1
LLM_EXTRACT_API_KEY=your-api-key-here
LLM_EXTRACT_MODEL=openai/gpt-4o
```

---

## Updating

To get the latest version of `llm-extract`, run:

```bash
uv tool install --reinstall git+https://github.com/destiny-evidence/llm-extract
```

Your credentials and config files are not affected by an update.

---

## Usage

```bash
llm-extract --file <text-file> --attrs <attributes-csv>
```

### Options

| Option | Required | Description |
|---|---|---|
| `--file` | Yes | Path to the text file to extract from |
| `--attrs` | Yes | Path to the CSV file defining the attributes |
| `--env` | No | Path to a `.env` file (overrides all other credential sources) |
| `--with-reasoning` | No | Enable chain-of-thought reasoning. Adds a `_reasoning_` row to the output explaining the extraction. Off by default. |
| `--output` | No | Where to write results. Pass a `.csv` file path for an exact destination, or a directory to auto-name the file as `<source>-extracted.csv`. If omitted, results are printed to the console. |

### Output format

Without `--output`, results are printed as an aligned table:

```
name          value
product_name  Aeron Chair by Herman Miller
price         1495.0
in_stock      True
```

With `--output`, results are written to a CSV with `name` and `value` columns:

```
name,value
product_name,Aeron Chair by Herman Miller
price,1495.0
in_stock,True
```

Two special values may appear:

- **`NOT_FOUND`** — the attribute was not present in the source text.
- **`_reasoning_`** — a final row containing the LLM's chain-of-thought explanation for the extraction. Only present when reasoning was produced.

### Defining attributes

The attributes CSV must have three columns:

| Column | Description |
|---|---|
| `name` | The attribute name (no spaces) |
| `type` | The Python type (see [Type reference](#type-reference) below) |
| `description` | A plain-English description of what to extract |

The description is important — the more specific it is, the more accurate the extraction. For example, instead of `"The price"`, use `"The price as a plain decimal number without currency symbols (e.g. 1495.0)"`.

### Type reference

There are four base types:

| Type | What it stores | Example value | When to use |
|---|---|---|---|
| `str` | Text | `Aeron Chair` | Names, labels, free-text fields |
| `int` | Whole number | `42` | Counts, years, quantities |
| `float` | Decimal number | `14.99` | Prices, measurements, ratings |
| `bool` | True or false | `True` | Flags, yes/no fields |

You can also ask for a **list** of any base type by writing `list[type]`. Use this when a field can hold multiple values rather than just one:

| Type | What it stores | Example value |
|---|---|---|
| `list[str]` | Multiple text values | `["red", "blue", "green"]` |
| `list[int]` | Multiple whole numbers | `[8, 10, 12]` |
| `list[float]` | Multiple decimal numbers | `[1.5, 2.0, 3.75]` |
| `list[bool]` | Multiple true/false values | `[True, False, True]` |

For example, `list[str]` is just `list[` + `str` + `]` — the same pattern works for any base type.

Finally, use `dict` when you want a set of named values grouped together (e.g. multiple dimensions each with their own label):

| Type | What it stores | Example value |
|---|---|---|
| `dict` | Named key-value pairs, any types | `{"label": "wide", "stock": 3}` |
| `dict[str, float]` | Named key-value pairs where keys are text and values are decimals | `{"width": 60.0, "depth": 65.0, "height": 94.0}` |
| `dict[str, int]` | Named key-value pairs where keys are text and values are whole numbers | `{"xs": 2, "m": 5, "xl": 1}` |

The pattern is `dict[key type, value type]` — you can use any base type for either side.

### Examples

Print results to the console:
```bash
llm-extract --file paper.txt --attrs fields.csv
```

Save to a specific file:
```bash
llm-extract --file paper.txt --attrs fields.csv --output results.csv
```

Save to a directory (auto-named `paper-extracted.csv`):
```bash
llm-extract --file paper.txt --attrs fields.csv --output /path/to/dir/
```

Use chain-of-thought reasoning:
```bash
llm-extract --file paper.txt --attrs fields.csv --with-reasoning
```

Use a specific `.env` file for credentials:
```bash
llm-extract --file paper.txt --attrs fields.csv --env /path/to/.env
```

---

## Troubleshooting

**`Missing required environment variables`** — one or more of `LLM_EXTRACT_API_BASE`, `LLM_EXTRACT_API_KEY`, or `LLM_EXTRACT_MODEL` is not set. Check your config file or pass `--env`.

**`Invalid value for '--file'`** — the file path you passed does not exist or cannot be read. Check the path and try again.

**`NOT_FOUND` in results** — the LLM could not locate that attribute in the source text. Consider making the description in your attributes CSV more specific.

**`Invalid value for '--output'`** — the directory you passed does not exist. Create it first, or pass a full file path instead.