import asyncio
from concurrent.futures import ThreadPoolExecutor

from flask import Flask, request, jsonify, send_from_directory, Response, stream_with_context
import subprocess
import os
import time
import re
import atexit
import signal
import threading
import queue
import json

app = Flask(__name__)

# Global variables for Q CLI process management
q_process = None
q_initialized = False
response_queue = queue.Queue()
stop_reading = threading.Event()
stdout_queue = queue.Queue()
stderr_queue = queue.Queue()


def enqueue_output(file, queue):
    while True:
        char = file.read(1)
        queue.put(char)
    file.close()


def read_output(process, q, stop_event):
    """Read output from the process in a separate thread"""
    print("Reading output")

    with ThreadPoolExecutor(2) as pool:
        q_stdout, q_stderr = queue.Queue(), queue.Queue()

        pool.submit(enqueue_output, process.stdout, q_stdout)
        pool.submit(enqueue_output, process.stderr, q_stderr)

        buffer = ""
        last_char_time = time.time()
        response_timeout = 30.0  # 3 seconds of inactivity indicates end of response
        chunk_buffer = ""

        while not stop_event.is_set():
            if process.poll() is not None:
                break

            try:
                char = q_stdout.get_nowait()
                chunk_buffer += char
                buffer += char
                last_char_time = time.time()

                # Send chunks more frequently for better streaming
                if len(chunk_buffer) >= 10 or char in '\n.!?':
                    q.put({"type": "chunk", "data": chunk_buffer})
                    chunk_buffer = ""

            except queue.Empty:
                current_time = time.time()

                # Send any remaining chunk buffer
                if chunk_buffer:
                    q.put({"type": "chunk", "data": chunk_buffer})
                    chunk_buffer = ""

                if buffer and (current_time - last_char_time) > response_timeout:
                    q.put({"type": "complete", "data": buffer})
                    buffer = ""

                time.sleep(0.01)

    print("End of Reading output")


def initialize_q_cli():
    """Initialize the Q CLI in chat mode and return the process object"""
    global q_process, q_initialized, stop_reading

    if q_process is not None and q_process.poll() is None:
        return "Q CLI already initialized"

    # Stop any existing reader thread
    stop_reading.set()

    # Reset the stop event for a new reader thread
    stop_reading = threading.Event()

    # Start the Q CLI in chat mode
    q_process = subprocess.Popen(
        ["q", "chat", "--trust-all-tools"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=0
    )

    # Start a thread to read the output
    reader_thread = threading.Thread(
        target=read_output,
        args=(q_process, response_queue, stop_reading)
    )
    reader_thread.daemon = True
    reader_thread.start()

    # Wait for the initial prompt
    try:
        # Give some time for the initial output to appear
        time.sleep(3)

        # Collect initial chunks until we get a complete message or timeout
        initial_output = ""
        start_time = time.time()
        timeout = 10  # 10 second timeout

        while time.time() - start_time < timeout:
            try:
                response_data = response_queue.get(timeout=0.5)

                if isinstance(response_data, dict):
                    if response_data.get("type") == "chunk":
                        initial_output += response_data.get("data", "")
                    elif response_data.get("type") == "complete":
                        initial_output = response_data.get("data", "")
                        break
                else:
                    # Legacy format
                    initial_output = response_data
                    break
            except queue.Empty:
                continue

        q_initialized = True
        print("Q CLI chat session initialized successfully")
        return initial_output
    except Exception as e:
        raise Exception(f"Failed to initialize Q CLI chat session: {str(e)}")


def is_q_session_alive():
    """Check if Q CLI session is alive and responsive"""
    global q_process, q_initialized

    if not q_initialized or q_process is None:
        return False

    if q_process.poll() is not None:
        return False

    return True


def send_query_to_q(query):
    """Send a query to the persistent Q CLI session"""
    global q_process

    if q_process and q_process.poll() is None:
        try:
            q_process.stdin.write(f"{query}\n")
            q_process.stdin.flush()
        except Exception as e:
            print(f"Error sending query to Q CLI: {e}")
            raise
    else:
        raise Exception("Q CLI process is not running")


def cleanup_q_process():
    """Clean up the Q CLI process on application exit"""
    global q_process, stop_reading

    # Signal the reader thread to stop
    stop_reading.set()

    if q_process is not None:
        try:
            # Send the quit command to gracefully exit
            if q_process.poll() is None:  # Only if process is still running
                q_process.stdin.write("/quit\n")
                q_process.stdin.flush()
                q_process.wait(timeout=5)
        except:
            # Force terminate if graceful exit fails
            try:
                q_process.terminate()
                q_process.wait(timeout=5)
            except:
                q_process.kill()
        print("Q CLI chat session terminated")


# Register the cleanup function to be called on exit
atexit.register(cleanup_q_process)

# Also handle SIGTERM for container environments
signal.signal(signal.SIGTERM, lambda signum, frame: cleanup_q_process())


@app.route('/')
def index():
    return send_from_directory('.', 'jj_agentic_ai_poc.html')


@app.route('/api/query', methods=['POST', 'GET'])
def query():
    global q_process, q_initialized

    # Handle both GET (for SSE) and POST requests
    if request.method == 'GET':
        user_query = request.args.get('query', '')
        streaming = True  # GET requests are always streaming
    else:  # POST
        data = request.json
        user_query = data.get('query', '')
        streaming = data.get('streaming', True)  # Default to streaming mode

    if not user_query:
        return jsonify({'response': 'Empty query received'}), 400

    try:
        # Initialize Q CLI if not already done
        if not q_initialized:
            initialize_q_cli()

        # Check if process is still alive and restart if needed
        if not is_q_session_alive():
            print("Q CLI session not alive. Restarting...")
            q_initialized = False
            initialize_q_cli()

        # Send the query to the persistent Q CLI session
        send_query_to_q(user_query)

        if streaming:
            # Use streaming response
            def generate():
                ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

                while True:
                    try:
                        response_data = response_queue.get(timeout=60)

                        if isinstance(response_data, dict):
                            response_type = response_data.get("type")
                            chunk = response_data.get("data", "")

                            if response_type == "chunk" and chunk:
                                # Clean ANSI escape sequences and send chunk
                                clean_chunk = ansi_escape.sub('', chunk)
                                if clean_chunk:  # Only send non-empty chunks
                                    yield f"data: {json.dumps({'chunk': clean_chunk})}\n\n"
                            elif response_type == "complete":
                                # Complete response received
                                clean_response = ansi_escape.sub('', chunk)
                                yield f"data: {json.dumps({'complete': clean_response.strip()})}\n\n"
                                break
                        else:
                            # Legacy format (just a string)
                            clean_response = ansi_escape.sub('', response_data)
                            yield f"data: {json.dumps({'complete': clean_response.strip()})}\n\n"
                            break

                    except queue.Empty:
                        yield f"data: {json.dumps({'error': 'Request timed out'})}\n\n"
                        break

            return Response(stream_with_context(generate()), mimetype='text/event-stream')
        else:
            # Use traditional non-streaming response
            try:
                response = None
                start_time = time.time()
                timeout = 60

                while time.time() - start_time < timeout:
                    try:
                        response_data = response_queue.get(timeout=1)

                        if isinstance(response_data, dict) and response_data.get("type") == "complete":
                            response = response_data.get("data", "")
                            break
                        elif isinstance(response_data, str):
                            response = response_data
                            break

                    except queue.Empty:
                        continue

                if response is None:
                    return jsonify({'response': 'Request timed out'}), 408

                # Clean ANSI escape sequences
                ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
                clean_response = ansi_escape.sub('', response)

                return jsonify({'response': clean_response.strip()})

            except Exception as e:
                return jsonify({'response': f'Error: {str(e)}'}), 500

    except Exception as e:
        return jsonify({'response': f"Server error: {str(e)}"}), 500


if __name__ == '__main__':
    try:
        # Initialize Q CLI on startup
        initialize_q_cli()
        app.run(debug=False, host='0.0.0.0', port=5001)  # Set debug=False to avoid multiple Q CLI processes
    except Exception as e:
        print(f"Error initializing Q CLI: {str(e)}")
        cleanup_q_process()
