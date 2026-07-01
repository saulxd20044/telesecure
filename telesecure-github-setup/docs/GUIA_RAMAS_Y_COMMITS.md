# Estrategia de Ramas, Commits y Protección de la Rama Principal

## 1. Modelo de ramas

Se adopta un modelo GitFlow simplificado:

```
main       Rama protegida. Siempre desplegable. Recibe cambios unicamente
           mediante Pull Request desde develop o desde una rama hotfix.

develop    Rama de integracion continua. Base para todas las ramas feature/*.

feature/infra-base
feature/despliegue-vm
feature/provisioning-webhook
feature/auditoria-iso
feature/documentacion-final

hotfix/<nombre>   Correcciones urgentes aplicadas directamente sobre main
                   (por ejemplo, una credencial expuesta o un fallo critico).
```

Regla general: ningún cambio se envía directamente a `main`. Todo ingresa
mediante Pull Request.

### Creación de la rama develop (una sola vez)

```bash
git checkout main
git pull origin main
git checkout -b develop
git push -u origin develop
```

### Flujo de trabajo por historia de usuario o Issue

```bash
git checkout develop
git pull origin develop
git checkout -b feature/provisioning-webhook
# desarrollo del cambio
git add .
git commit -m "feat(webhook): valida token X-Auth-Token antes de aprovisionar"
git push -u origin feature/provisioning-webhook
# abrir Pull Request: feature/provisioning-webhook -> develop
```

---

## 2. Convención de commits (Conventional Commits)

Formato: `tipo(alcance): descripción breve en modo imperativo`.

| Tipo | Uso |
|---|---|
| feat | Nueva funcionalidad |
| fix | Corrección de un defecto |
| docs | Cambios exclusivos en documentación |
| chore | Mantenimiento (dependencias, configuración, `.gitignore`) |
| test | Adición o corrección de pruebas |
| refactor | Cambios de código sin alterar el comportamiento |
| security | Cambios de endurecimiento de seguridad |

Ejemplos aplicados a este repositorio:

```
feat(midpoint): agrega notificador customTransport para el evento de asignacion de rol
fix(webhook): corrige permisos DML del usuario mp_user sobre la base asterisk
security(freepbx): fuerza TLS 1.2 y SRTP en el transporte pjsip
docs(fase4): agrega resultados de la auditoria con Trivy
chore(gitignore): excluye archivos de credenciales de laboratorio
```

---

## 3. Protección de la rama main

Configuración en el repositorio: Settings > Branches > Add branch protection
rule, con el patrón `main`.

Opciones a habilitar:

- Require a pull request before merging (aprobaciones mínimas: una; puede
  reducirse a cero si el proyecto se desarrolla de forma individual, pero se
  recomienda mantener el registro del Pull Request).
- Require status checks to pass before merging, seleccionando el check `tests`
  definido en `.github/workflows/ci.yml`.
- Require branches to be up to date before merging.
- Require conversation resolution before merging.
- Do not allow bypassing the above settings (incluye a los administradores).
- Restrict deletions.
- Block force pushes.

Se recomienda aplicar la misma regla a `develop`, con exigencias menos
estrictas si se trabaja en solitario (por ejemplo, sin aprobaciones
obligatorias, pero manteniendo la integración continua como requisito).

### Configuración equivalente por API (GitHub CLI)

```bash
gh api -X PUT repos/saulxd20044/telesecure/branches/main/protection \
  -H "Accept: application/vnd.github+json" \
  -f required_status_checks[strict]=true \
  -f required_status_checks[contexts][]=tests \
  -f enforce_admins=true \
  -f required_pull_request_reviews[required_approving_review_count]=1 \
  -f restrictions=null
```

---

## 4. Gestión de archivos sensibles

Se identificó que `midpoint/keystore_password.txt` y
`midpoint/repo_password.txt` se encuentran versionados en `main`. Actualmente
están vacíos, pero representan un riesgo: si en algún momento se completan
localmente y se incluyen en un commit sin revisión previa, quedarían expuestos
de forma permanente en el historial del repositorio.

Acción correctiva:

```bash
git rm --cached midpoint/keystore_password.txt midpoint/repo_password.txt
```

Y la incorporación de las siguientes reglas en `.gitignore`:

```
# Credenciales de laboratorio, no deben versionarse
*password*.txt
*.pem
*.key
keystore/
```

Si en algún commit anterior estos archivos llegaron a contener información
real, es necesario purgarlos del historial mediante `git filter-repo` y rotar
las credenciales correspondientes; eliminarlos en un commit nuevo no es
suficiente, dado que el contenido permanecería accesible en el historial.

Se recomienda además habilitar Secret Scanning y Push Protection en Settings >
Security, disponible sin costo en repositorios públicos.
