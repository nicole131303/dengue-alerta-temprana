# Convenciones del proyecto

Aunque la tesis es individual, el repositorio se trabaja **como si fuera un equipo**: cada
cambio pasa por una rama, un Pull Request y la integración continua. Así el historial de
GitHub se convierte en la bitácora verificable del avance experimental.

## 1. Flujo de trabajo (GitHub Flow)

```
main (siempre funciona, protegida)
 ├── feat/12-vecinos-lag2      ← una rama por issue, vive horas o pocos días
 ├── fix/15-ubigeo-ceros
 └── exp/18-ablacion-real
```

1. Crear o elegir un **issue** (`gh issue list`).
2. Crear rama desde `main` actualizado: `git switch main && git pull && git switch -c feat/12-vecinos-lag2`.
3. Programar + prueba automática. Correr `make lint test` (o `ruff check . && pytest`).
4. Commits pequeños con mensajes convencionales (abajo).
5. `git push -u origin feat/12-vecinos-lag2` y abrir PR (`gh pr create --fill`).
6. Esperar la CI en verde ✅, revisar el diff propio y fusionar con **Squash and merge**.
7. Borrar la rama. El issue se cierra solo si el PR dice `Cierra #12`.

## 2. Nombres de ramas

`<tipo>/<número-issue>-<descripción-corta>` → `feat/7-clima-gee`, `fix/9-semana-53`, `exp/14-optuna-h4`, `docs/3-guia`.

## 3. Mensajes de commit ([Conventional Commits](https://www.conventionalcommits.org/es/v1.0.0/))

```
<tipo>(<ámbito>): <qué cambia, en imperativo y minúsculas>

<por qué (opcional)>

Cierra #12
```

| Tipo | Cuándo | Ejemplo |
|---|---|---|
| `feat` | Funcionalidad nueva | `feat(features): agregar casos de vecinos con rezago de 2 semanas` |
| `fix` | Corrección | `fix(panel): conservar el cero inicial del ubigeo al leer CSV` |
| `exp` | Experimento o cambio de configuración | `exp(config): probar brote con 4 semanas consecutivas` |
| `test` | Solo pruebas | `test(fuga): cubrir variables climáticas` |
| `refactor` | Reorganizar sin cambiar resultados | `refactor(modelado): extraer fábrica de modelos` |
| `docs` | Documentación | `docs: explicar rezago de publicación del ICEN` |
| `chore` / `ci` | Mantenimiento / GitHub Actions | `ci: agregar Python 3.12 a la matriz` |

Ámbitos: `datos`, `panel`, `features`, `modelado`, `app`, `config`, `ci`.

## 4. Estilo de código

- **Formato y linter:** `ruff` (se ejecuta solo con `pre-commit`). Líneas de 100 caracteres.
- **Nombres en español** y descriptivos (`casos_vecinos`, no `cv`); consistentes con la tesis.
- **Type hints** en funciones públicas y **docstring** que diga *qué* hace y *por qué*.
- **Sin números mágicos**: todo parámetro va a `configs/`.
- **Funciones puras** cuando se pueda: reciben DataFrame, devuelven DataFrame, no leen archivos.
  La lectura/escritura vive en `pipeline.py` e `io.py`.
- **Logging, no print**: `log = obtener_logger(__name__)`.

## 5. Pruebas

- Toda función nueva en `src/` lleva al menos una prueba en `tests/test_<módulo>.py`.
- Nombre de la prueba = la regla que verifica: `test_dos_ceros_cierran_el_episodio`.
- Toda variable nueva debe pasar `tests/test_fuga.py` (no puede mirar el futuro).
- Pruebas lentas se marcan con `@pytest.mark.lento` (se omiten con `pytest -m "not lento"`).

## 6. Definición de "terminado"

- [ ] CI en verde
- [ ] Prueba automática que demuestra el comportamiento
- [ ] Parámetros en YAML
- [ ] Docstring y, si cambia la metodología, una nota en `docs/decisiones/`
- [ ] Entrada en `CHANGELOG.md` si es visible para el usuario

## 7. Lo que nunca se sube

Datos (`data/`), modelos (`models/`), resultados generados (`reports/`), `.env`, credenciales
de Earth Engine. `.gitignore` y el hook `check-added-large-files` lo impiden.
