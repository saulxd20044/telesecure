# Guía de Contribución

Este proyecto se desarrolla bajo el marco Scrum (sprints semanales, cada uno
asociado a un milestone de GitHub) y un flujo de ramas tipo GitFlow
simplificado. Antes de contribuir, revisar:

- `docs/PLAN_SCRUM_HITOS.md`: sprints, hitos y definición de terminado.
- `docs/GUIA_RAMAS_Y_COMMITS.md`: ramas, convención de commits y protección de
  la rama principal.
- `docs/HISTORIAS_USUARIO.md`: backlog priorizado del proyecto.

## Flujo de trabajo

1. Seleccionar una historia de usuario del backlog o crear un Issue con la
   plantilla correspondiente.
2. Crear la rama de trabajo a partir de `develop`:
   `git checkout develop && git pull && git checkout -b feature/<nombre>`.
3. Registrar los cambios con commits que sigan la convención Conventional
   Commits (`feat`, `fix`, `docs`, `security`, `chore`, `test`).
4. Abrir un Pull Request contra `develop`, usando la plantilla del
   repositorio y referenciando el Issue correspondiente (`Closes #N`).
5. Esperar a que la integración continua finalice sin errores y a que el
   cambio sea revisado.
6. Al completar todos los Issues del milestone activo: abrir un Pull Request
   de `develop` hacia `main`, generar la etiqueta de versión correspondiente y
   cerrar el milestone.

## Reglas del repositorio

- No se realizan push directos a `main`.
- No se versionan archivos `.env`, contraseñas ni certificados privados
  (ver `.gitignore`).
- Todo cambio en `webhook/` debe mantener en estado exitoso la ejecución de
  `python3 -m unittest test_webhook_provisioner -v`.
