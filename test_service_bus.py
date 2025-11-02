import os
import sys
import asyncio
from dotenv import load_dotenv
from azure.servicebus.aio import ServiceBusClient
from azure.servicebus import ServiceBusMessage

# Load environment variables from .env file
load_dotenv()

# Get connection string from environment
CONNECTION_STRING = os.environ.get("AZURE_SERVICE_BUS_CONNECTION_STRING")
QUEUE_NAME = "module-generation"  # Use your queue name

async def send_message():
    # Create a Service Bus client using the connection string
    async with ServiceBusClient.from_connection_string(
        conn_str=CONNECTION_STRING,
        logging_enable=True
    ) as servicebus_client:
        # Get a Queue Sender object to send messages to the queue
        sender = servicebus_client.get_queue_sender(queue_name=QUEUE_NAME)
        async with sender:
            # Create a test message
            message = ServiceBusMessage("Test message from SkillSync")
            print("Sending test message...")
            # Send the message
            await sender.send_messages(message)
            print("Message sent!")

async def receive_message():
    # Create a Service Bus client using the connection string
    async with ServiceBusClient.from_connection_string(
        conn_str=CONNECTION_STRING,
        logging_enable=True
    ) as servicebus_client:
        # Get a Queue Receiver object to receive messages from the queue
        receiver = servicebus_client.get_queue_receiver(queue_name=QUEUE_NAME)
        async with receiver:
            print("Waiting for messages...")
            # Receive messages for 5 seconds
            received_msgs = await receiver.receive_messages(max_message_count=10, max_wait_time=5)
            
            for msg in received_msgs:
                print(f"Received: {str(msg)}")
                # Complete the message so it is removed from the queue
                await receiver.complete_message(msg)

async def main():
    if len(sys.argv) > 1 and sys.argv[1] == "receive":
        await receive_message()
    else:
        await send_message()

if __name__ == "__main__":
    # Run the async function
    asyncio.run(main())