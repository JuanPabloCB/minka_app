# app/core/constants.py

UI_BULLETS_CATALOG = {
  # Métodos de input (lo que el usuario podra hacer a la fecha de la primera version del MVP)
  "available_inputs": {
    "title": "Por ahora puedes enviar tu información así:",
    "variant": "bullets",
    "items": [
      "Subir archivo desde tu computadora",
      "Pegar texto directamente en el chat",
      "Importar archivo desde Google Drive",
    ],
  },

  # Formatos permitidos cuando el input es archivo
  "supported_input_file_formats": {
    "title": "Formatos de archivo soportados:",
    "variant": "bullets",
    "items": ["PDF (.pdf)", "Word (.docx)", "Texto (.txt)"],
  },

  # Formatos de salida/exportación
  "supported_output_formats": {
    "title": "Formatos de exportación disponibles:",
    "variant": "bullets",
    "items": ["PDF (.pdf)", "Word (.docx)"],
  },
}