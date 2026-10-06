import json
from pathlib import Path
from deep_translator import GoogleTranslator

def translate_markdown_source(lines, translator):
    """Traduce una lista de líneas Markdown de EN a ES, manteniendo saltos."""
    translated_lines = []
    for line in lines:
        # No tocamos líneas vacías
        if not line.strip():
            translated_lines.append(line)
            continue

        # Intentamos traducir la línea; si falla, la dejamos tal cual
        try:
            # GoogleTranslator acepta cadenas completas; devolvemos con \n
            translated = translator.translate(line)
            translated_lines.append(translated + ("\n" if not line.endswith("\n") else ""))
        except Exception as e:
            print(f"[AVISO] No se pudo traducir la línea: {line!r} -> {e}")
            translated_lines.append(line)

    return translated_lines

def translate_notebook_en_to_es(input_path, output_path):
    input_path = Path(input_path)
    output_path = Path(output_path)

    # Cargamos el notebook
    with input_path.open("r", encoding="utf-8") as f:
        nb = json.load(f)

    translator = GoogleTranslator(source="en", target="es")

    num_cells = len(nb.get("cells", []))
    num_md_cells = 0

    for i, cell in enumerate(nb.get("cells", [])):
        if cell.get("cell_type") == "markdown":
            num_md_cells += 1
            original = cell.get("source", [])

            print(f"Traduciendo celda Markdown {num_md_cells}/{num_cells}...")
            cell["source"] = translate_markdown_source(original, translator)

    # Guardamos el notebook traducido
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(nb, f, ensure_ascii=False, indent=1)

    print(f"\n✅ Traducción completada.")
    print(f" - Celdas totales: {num_cells}")
    print(f" - Celdas Markdown traducidas: {num_md_cells}")
    print(f" - Notebook guardado en: {output_path}")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Traducir celdas Markdown de un Jupyter Notebook EN → ES.")
    parser.add_argument("input_nb", help="Notebook de entrada (.ipynb) en inglés")
    parser.add_argument(
        "-o", "--output",
        help="Notebook de salida (.ipynb) traducido al castellano. Por defecto añade _es al nombre."
    )

    args = parser.parse_args()
    input_nb = Path(args.input_nb)

    if args.output:
        output_nb = Path(args.output)
    else:
        output_nb = input_nb.with_name(input_nb.stem + "_es.ipynb")

    translate_notebook_en_to_es(input_nb, output_nb)
