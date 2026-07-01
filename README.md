# llm-extract

Extract structured data from text files and PDFs using large language models. You define the attributes you want to extract in a simple CSV file, and `llm-extract` pulls them out for you.

## What it does

Given a text file or PDF (or folder of files) and a CSV (or Excel file) describing the attributes you want, `llm-extract` uses an LLM to read the document and return the values. Works with plain text files, markdown, HTML, and PDFs.

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

**Extract from a single file:**
```bash
llm-extract file --source sample.txt --attrs attributes.csv
```

**Extract from a folder of files (concurrently):**
```bash
llm-extract folder --source ./documents --attrs attributes.csv
```

**Example output:**
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

**For PDF extraction:** use a vision-capable model like `gpt-4o`, `claude-3-5-sonnet-20241022`, or `gemini-2.0-flash`. Regular models (e.g., `gpt-3.5-turbo`) only work with plain text files.

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

### Extract from a single file

```bash
llm-extract file --source <text-file> --attrs <attributes-csv>
```

### Extract from a folder (concurrently)

```bash
llm-extract folder --source <folder> --attrs <attributes-csv>
```

**For project-driven workflows** — extract recursively from all subdirectories:

```bash
llm-extract folder --source <project-root> --attrs <attributes-csv> --recursive
```

This traverses all subdirectories and recreates the folder structure in the output, perfect for processing entire projects or nested document hierarchies.

### Common options

| Option | Required | Description |
|---|---|---|
| `--source` | Yes | Path to the text file or folder to extract from |
| `--attrs` | Yes | Path to the CSV file defining the attributes, or an Excel workbook defining custom types (see [Custom types](#custom-types-excel-templates)) |
| `--type` | Depends | Name of the top-level sheet to extract. Required when `--attrs` is an Excel workbook. |
| `--env` | No | Path to a `.env` file (overrides all other credential sources) |
| `--with-reasoning` | No | Enable chain-of-thought reasoning. Adds a `_reasoning_` row to the output explaining the extraction. Off by default. |
| `--output` | No | **File mode:** Where to write results. Pass a `.csv` or `.xlsx` file path, or a directory to auto-name the file. If omitted, results print to console. **Folder mode:** Directory to write results to. Each file becomes `<filename>-extracted.csv` or `.xlsx`. Defaults to `<source>-extracted/` in the same parent directory. |

### Folder-only options

| Option | Default | Description |
|---|---|---|
| `--filetype` | `txt` | File type(s) to process. Pass multiple times for multiple types: `--filetype txt --filetype md --filetype pdf`. Supported: `txt`, `md`, `html`, `pdf` (requires vision model). |
| `--max-concurrent` | `8` | Maximum number of concurrent extractions. Use this to control resource usage or respect API rate limits. |
| `--recursive` | `false` | Recursively traverse subdirectories and preserve directory structure in output. Useful for processing entire projects. |

### Output format

#### Console

Without `--output`, results are printed as an aligned table:

```
name          value
product_name  Aeron Chair by Herman Miller
price         1495.0
in_stock      True
```

If `--attrs` is an Excel template (see [Custom types](#custom-types-excel-templates)), plain attributes are shown the same way, but any attribute with a custom type is shown as its own titled table underneath, with one row per item:

```
name           value
interventions  see 'interventions' table below

interventions
group_name   intervention_type.type_of_intervention
-----------  ---------------------------------------
Risperidone  Intervention
Haloperidol  NOT_FOUND
```

Tables wider than your terminal are printed as one `column: value` block per item instead of a grid.

#### CSV (`--output results.csv`)

Results are written to a CSV with `name` and `value` columns:

```
name,value
product_name,Aeron Chair by Herman Miller
price,1495.0
in_stock,True
```

Custom-type attributes are JSON-encoded in their cell.

#### Excel (`--output results.xlsx`)

Results are written to a multi-sheet workbook:

- A **"Summary"** sheet has one row per top-level attribute. Plain attributes show their value directly.
- Attributes with a custom type (or a non-empty list of one) get a hyperlink in the Summary sheet to a dedicated sheet, with one row per item and one column per field.
- Fields that are themselves a custom type one level deep are flattened into dot-prefixed columns (e.g. `intervention_type.type_of_intervention`). Any deeper nesting falls back to a JSON-encoded cell.
- Custom-type attributes with no value show `NOT_FOUND` in the Summary sheet, with no dedicated sheet created.

Two special values may appear in any output format:

- **`NOT_FOUND`** — the attribute was not present in the source text.
- **`_reasoning_`** — a row containing the LLM's chain-of-thought explanation for the extraction (last row in CSV/Summary). Only present when `--with-reasoning` was used.

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

Use `Literal` when a field should only ever be one of a fixed set of options (e.g. a category or status), rather than free text:

| Type | What it stores | Example value |
|---|---|---|
| `Literal["small", "medium", "large"]` | One of a fixed set of text options | `medium` |

This constrains the LLM to pick one of the listed values instead of generating arbitrary text.

### Custom types (Excel templates)

For more structured extractions — e.g. a study with multiple interventions, each with their own fields — pass an Excel workbook (`.xlsx` or `.xlsm`) as `--attrs` instead of a CSV.

Each **sheet** in the workbook defines a custom type: the sheet name is the type name, and each row defines one field of that type using the same `name`, `type`, `description` columns as a CSV. A field's `type` can reference another sheet by name to nest that type, or `list[OtherSheet]` for a list of that type.

Use `--type` to choose which sheet is the top-level type to extract.

**Example workbook:**

`Study` sheet:
```
name,type,description
title,str,The title of the study
interventions,list[Intervention],The interventions compared in the study
```

`Intervention` sheet:
```
name,type,description
group_name,str,The name of the intervention group
intervention_type,InterventionType,Details of the intervention type
```

`InterventionType` sheet:
```
name,type,description
type_of_intervention,str,e.g. drug, placebo, surgery, behavioural therapy
```

**Run:**
```bash
llm-extract --file paper.txt --attrs template.xlsx --type Study
```

Custom types can be referenced from any sheet, but circular references (a type that references itself, directly or indirectly) and references to sheets that don't exist will raise an error.

### PDF extraction (multimodal)

`llm-extract` can extract from PDFs in addition to plain text. Each PDF page is intelligently processed to optimize costs:

**Requirements:**
- Use a **vision-capable LLM model** (e.g., `gpt-4o`, `claude-3-5-sonnet`, `gemini-2.0-flash`)
- Non-vision models (e.g., `gpt-3.5-turbo`) will raise an error if you try to extract from PDFs

**How it works:**
1. PDFs are processed page-by-page using pdfplumber
2. For each page, `llm-extract` attempts to extract text
3. If the text extraction quality is high (readable text), it's used directly for extraction (cost-efficient)
4. If the text quality is low (diagrams, complex tables, unreadable layout), the page is rendered as an image and sent to the vision model
5. This hybrid approach optimizes costs by using text whenever possible, and images only when necessary

**For Word/PowerPoint/Excel files:** Convert them to PDF first (using your preferred tool), then extract from the PDF.

**Examples:**

Extract from a PDF:
```bash
llm-extract file --source research-paper.pdf --attrs fields.csv
```

Extract from folder of PDFs and text files:
```bash
llm-extract folder --source ./documents --attrs fields.csv \
  --filetype txt --filetype pdf
```

Supported formats:
- **Text:** `.txt`, `.md`, `.html`
- **PDF (requires vision model):** `.pdf`

### Examples

**Single file — print to console:**
```bash
llm-extract file --source paper.txt --attrs fields.csv
```

**Single file — save to CSV:**
```bash
llm-extract file --source paper.txt --attrs fields.csv --output results.csv
```

**Single file — save to directory (auto-named):**
```bash
llm-extract file --source paper.txt --attrs fields.csv --output /path/to/dir/
```

**Single file — with Excel template and custom types:**
```bash
llm-extract file --source paper.txt --attrs template.xlsx --type Study --output results.xlsx
```

**Folder — extract all .txt files concurrently:**
```bash
llm-extract folder --source ./documents --attrs fields.csv
```
Results are written to `./documents-extracted/` with one file per result.

**Folder — extract multiple file types:**
```bash
llm-extract folder --source ./documents --attrs fields.csv --filetype txt --filetype md
```

**Folder — custom concurrency and output:**
```bash
llm-extract folder --source ./documents --attrs fields.csv --max-concurrent 4 --output ./results/
```

**Folder — recursive extraction from project:**
```bash
llm-extract folder --source ./my-project --attrs fields.csv --recursive
```
Extracts from all subdirectories and recreates folder structure in `./my-project-extracted/`.

**Any mode — use chain-of-thought reasoning:**
```bash
llm-extract file --source paper.txt --attrs fields.csv --with-reasoning
```

**Any mode — use a specific `.env` file:**
```bash
llm-extract folder --source ./docs --attrs fields.csv --env /path/to/.env
```

---

## Troubleshooting

**`Missing required environment variables`** — one or more of `LLM_EXTRACT_API_BASE`, `LLM_EXTRACT_API_KEY`, or `LLM_EXTRACT_MODEL` is not set. Check your config file or pass `--env`.

**`Invalid value for '--file'`** — the file path you passed does not exist or cannot be read. Check the path and try again.

**`NOT_FOUND` in results** — the LLM could not locate that attribute in the source text. Consider making the description in your attributes CSV more specific.

**`Invalid value for '--output'`** — the directory you passed does not exist. Create it first, or pass a full file path instead.

**`--type is required when --attrs is an Excel workbook`** — pass `--type <SheetName>` to choose the top-level sheet to extract.

**`No sheet named '...' was found`** — a `type` column references a sheet that doesn't exist in the workbook. Check the spelling matches the sheet name exactly.

**`Circular type reference detected`** — two or more sheets reference each other (directly or via other sheets), which can't be resolved into a fixed structure. Remove the cycle from your template.