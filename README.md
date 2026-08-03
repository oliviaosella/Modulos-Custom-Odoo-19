# Módulos Odoo - Equipo

Repositorio con los módulos de Odoo en los que trabaja el equipo.

## Regla principal

**Sólo se sube al repo lo que ya fue probado en una base y funciona sin errores.**

Antes de hacer `push`:

1. Probá el módulo en una base de test (no en producción).
2. Verificá que instale/actualice sin errores.
3. Verificá que la funcionalidad principal que tocaste ande correctamente.
4. Recién ahí subilo al repo.

Si encontrás un problema y no llegaste a resolverlo, **no lo subas**. Avisá en el grupo del equipo para que quede claro que ese módulo está en curso.

## Cómo trabajar

- Antes de empezar a modificar algo, hacé `git pull` para tener la última versión.
- Trabajá y probá tus cambios localmente.
- Cuando esté probado y funcionando, hacé `git push`.

## Mensajes de commit

Usá un mensaje breve que indique qué módulo tocaste y qué hiciste, por ejemplo:

```
fix: modulo_ventas - corregido error en cálculo de descuento
```

```
feat: modulo_stock - nuevo reporte de inventario
```

Esto ayuda a que cualquiera del equipo pueda entender el historial de cambios de un vistazo.

## Si algo se rompe

Como todo queda versionado con git, si un módulo sube con un problema que no se detectó, se puede volver a la versión anterior sin drama. Avisá en el grupo apenas se detecte para que nadie más actualice ese módulo mientras se corrige.
