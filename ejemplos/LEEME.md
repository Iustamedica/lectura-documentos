# Ejemplos

## Modo salud

- **`salud/caso.ejemplo.json`**: ficha de titulares del **modo salud** (datos
  ficticios). Para usarla, cópiala como `caso.json` en la carpeta de trabajo del
  modo salud:

  ```bash
  cp ejemplos/salud/caso.ejemplo.json "Mi expediente/caso.json"
  ```

  La presencia de `caso.json` en una carpeta hace que la herramienta use el
  perfil **salud** automáticamente.

## Modo judicial (legal)

No necesita este archivo. Es el modo por defecto; para forzarlo en una carpeta
concreta, crea un `perfil.txt` con el texto `legal`.
