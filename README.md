# Dashboard Adolfo Domínguez · Ventas · Stock · Sell-through · Low Rotation

Dashboard de **Streamlit** que lee desde **MongoDB** y muestra ventas, stock,
sell-through, alertas de **baja rotación** y filtros por bodega, estilo, género,
familia y rango de fechas.

> El proceso ETL (SQL Server → MongoDB) corre por separado, en local/servidor con
> una tarea programada (`cron`). **No forma parte de este repositorio.** El
> dashboard solo **lee** de MongoDB, así que es rápido y no toca la red interna.

## Estructura

```
dashboard_ad/
├── dashboard/
│   └── app.py                  # Dashboard Streamlit (lee de MongoDB)
├── requirements.txt
├── .streamlit/
│   └── secrets.toml.example    # Plantilla de secrets (la real NO se sube)
└── .gitignore
```

## Configuración

El dashboard necesita dos secrets:

| Secret | Descripción |
|---|---|
| `APP_PASSWORD` | Contraseña para entrar al dashboard |
| `MONGO_URI` | Cadena de conexión a MongoDB |

### Local

```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # edita tus valores
streamlit run dashboard/app.py
```

También puedes pasar los secrets como variables de entorno
(`APP_PASSWORD`, `MONGO_URI`) en lugar del archivo `secrets.toml`.

### Streamlit Community Cloud

1. Conecta este repositorio y apunta a `dashboard/app.py`.
2. En **Settings → Secrets**, pega:
   ```toml
   APP_PASSWORD = "tu-contraseña"
   MONGO_URI = "mongodb+srv://usuario:PASSWORD@cluster0.../"
   ```

## Actualización de datos

- El **ETL** (fuera de este repo) actualiza MongoDB de forma programada con `cron`.
- El dashboard se **auto-recarga cada hora** para mostrar la data nueva sin
  reinicio manual; además hay un botón **«Actualizar datos»** para forzarlo.

## Seguridad

- Las credenciales **no van en el código**: se leen de `st.secrets` o de variables
  de entorno.
- `.streamlit/secrets.toml` está en `.gitignore` y nunca debe subirse.
