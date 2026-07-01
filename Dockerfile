# ---- Build frontend ----
    FROM node:20-alpine AS frontend-builder
    WORKDIR /build/frontend
    
    COPY frontend/package.json frontend/package-lock.json ./
    
    RUN npm ci
    RUN npm audit fix || true
    
    COPY frontend/ .
    RUN npm run build
    
    # ---- Build backend & run ----
    FROM python:3.11-slim
    WORKDIR /app
    
    # Copy backend source
    COPY backend/ .
    
    # Copy pre-built frontend to the path Flask expects (../frontend/build relative to /app)
    COPY --from=frontend-builder /build/frontend/build/ /frontend/build/
    
    # Install Python deps and run audit + auto-fix
    RUN pip install --no-cache-dir -r requirements.txt && python fix_audit.py
    
    EXPOSE 5000
    
    # Run with waitress in production
    CMD ["python", "wsgi.py"]