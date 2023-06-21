import socket

def chatbot_client():
    # Create a socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Connect to the server
    host = 'localhost'
    port = 30002
    s.connect((host, port))

    while True:
        # Get user input
        question = input("Please enter your question (or 'quit' to exit): ")
        if question == 'quit':
            break

        # Send the question to the server
        s.sendall(question.encode())

        # Receive and print the response from the server
        data = s.recv(1024)
        print('Response from server: ', data.decode())

    # Close the connection
    s.close()

if __name__ == "__main__":
    chatbot_client()
