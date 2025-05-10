from app import app, init_dropbox, init_pdf_processor, logger

if __name__ == "__main__":
    # Inicializar o Dropbox e o processador de PDF
    success = init_dropbox() and init_pdf_processor()
    
    if not success:
        logger.error("Falha ao inicializar os componentes necessários. Verifique os logs para mais detalhes.")
        exit(1)
    
    # Iniciar o servidor Flask
    app.run(host="0.0.0.0", port=5000, debug=False)  # Desabilitado debug para evitar reinicializações
