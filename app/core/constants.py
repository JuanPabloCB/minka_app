# app/core/constants.py

UI_BULLETS_CATALOG = {
  # Métodos de input (lo que el usuario podra hacer a la fecha de la primera version del MVP)
  "available_inputs": {
    "title": "Por ahora puedes enviar tu información así:",
    "variant": "bullets",
    "items": [
      "Subir archivo desde tu computadora",
#      "Pegar texto directamente en el chat",
#      "Importar archivo desde Google Drive",
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

SUPPORTED_INPUT_SOURCES = {
#  "paste_text": "paste_text",
#  "pegar texto": "paste_text",
#  "texto en el chat": "paste_text",
#  "chat": "paste_text",
  "local_upload": "local_upload",
  "subir archivo": "local_upload",
  "archivo local": "local_upload",
  "pending":"pending",
  "pendiente":"pending",
  "aun no lo tengo":"pending",
  "aún no lo tengo":"pending",
  "falta":"pending",
 # "google drive": "google_drive",
#  "gdrive": "google_drive",
#  "drive": "google_drive",
}

SUPPORTED_OUTPUT_FORMATS = {
  "pdf": "pdf",
  ".pdf": "pdf",
  "docx": "docx",
  ".docx": "docx",
  "word": "docx",
  "word (.docx)": "docx",
}