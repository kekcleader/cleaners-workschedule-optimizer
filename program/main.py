from services import app, generate_demo_data

if __name__ == "__main__":
    generate_demo_data()
    app.run(debug=True, host='0.0.0.0', port=5000)