import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import requests
from bs4 import BeautifulSoup
import threading
import time
import re
import os
from datetime import datetime
import queue

class TelegramMessenger:
    def __init__(self, token, chat_id):
        self.token = token
        self.chat_id = chat_id
        self.message_queue = queue.Queue()
        self.is_sending = False

    def start_sending_thread(self):
        threading.Thread(target=self.process_queue, daemon=True).start()

    def process_queue(self):
        self.is_sending = True
        while True:
            message, delay = self.message_queue.get()
            self.send_message(message)
            time.sleep(delay)

    def send_message(self, message):
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "Markdown",
        }
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Error sending message: {e}")

    def queue_message(self, message):
        self.message_queue.put((message, 30))


class WebshopFinderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CARDABLE WEBSHOP FINDER                                              [Tool Created by: t.me/hofnar05_Worm_GPT_bot]")
        self.root.geometry("750x500")
        self.root.resizable(True, True)

        self.keywords_file = ""
        self.payment_providers_file = ""
        self.telegram_messenger = None

        self.search_thread = None

        # Create widgets
        self.create_widgets()

    def create_widgets(self):
        padding = {'padx': 10, 'pady': 5}

        # Telegram Token Input
        self.telegram_token_label = tk.Label(self.root, text="Telegram Token [Optional]:")
        self.telegram_token_entry = tk.Entry(self.root, width=50)

        self.telegram_token_label.grid(row=0, column=0, sticky='e', **padding)
        self.telegram_token_entry.grid(row=0, column=1, columnspan=2, **padding)

        # Telegram Chat ID Input
        self.telegram_id_label = tk.Label(self.root, text="Telegram Chat ID [Optional]:")
        self.telegram_id_entry = tk.Entry(self.root, width=50)

        self.telegram_id_label.grid(row=1, column=0, sticky='e', **padding)
        self.telegram_id_entry.grid(row=1, column=1, columnspan=2, **padding)

        # Keywords File Selection
        self.keywords_label = tk.Label(self.root, text="Keywords File (keywords.txt):")
        self.keywords_entry = tk.Entry(self.root, width=50)
        self.keywords_browse_button = tk.Button(self.root, text="Browse", command=self.browse_keywords)

        self.keywords_label.grid(row=2, column=0, sticky='e', **padding)
        self.keywords_entry.grid(row=2, column=1, **padding)
        self.keywords_browse_button.grid(row=2, column=2, **padding)

        # Payment Providers File Selection
        self.payment_providers_label = tk.Label(self.root, text="Payment Providers File (payment_providers.txt):")
        self.payment_providers_entry = tk.Entry(self.root, width=50)
        self.payment_providers_browse_button = tk.Button(self.root, text="Browse", command=self.browse_payment_providers)

        self.payment_providers_label.grid(row=3, column=0, sticky='e', **padding)
        self.payment_providers_entry.grid(row=3, column=1, **padding)
        self.payment_providers_browse_button.grid(row=3, column=2, **padding)

        # Search Button
        self.search_button = tk.Button(self.root, text="Start Search", command=self.start_search, bg="green", fg="white", font=('Arial', 12, 'bold'))
        self.search_button.grid(row=5, column=1, pady=20)

        # Status Label
        self.status_label = tk.Label(self.root, text="Status: Idle", fg="blue")
        self.status_label.grid(row=6, column=0, columnspan=3, **padding)

        # Live Results Text Box
        self.results_text = scrolledtext.ScrolledText(self.root, width=80, height=10, state='disabled')
        self.results_text.grid(row=7, column=0, columnspan=3, pady=10)

    def browse_keywords(self):
        file_path = filedialog.askopenfilename(
            initialdir=".",
            title="Select Keywords File",
            filetypes=(("Text Files", "*.txt"), ("All Files", "*.*"))
        )
        if file_path:
            self.keywords_file = file_path
            self.keywords_entry.delete(0, tk.END)
            self.keywords_entry.insert(0, self.keywords_file)

    def browse_payment_providers(self):
        file_path = filedialog.askopenfilename(
            initialdir=".",
            title="Select Payment Providers File",
            filetypes=(("Text Files", "*.txt"), ("All Files", "*.*"))
        )
        if file_path:
            self.payment_providers_file = file_path
            self.payment_providers_entry.delete(0, tk.END)
            self.payment_providers_entry.insert(0, self.payment_providers_file)

    def start_search(self):
        if not (self.keywords_file and self.payment_providers_file):
            messagebox.showwarning("Input Missing", "Please select all input files.")
            return

        # Get Telegram details from user input
        token = self.telegram_token_entry.get().strip()
        chat_id = self.telegram_id_entry.get().strip()

        if token and chat_id:
            self.telegram_messenger = TelegramMessenger(token, chat_id)
            self.telegram_messenger.start_sending_thread()

        # Create results directory based on current date and time
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_dir = os.path.join(os.getcwd(), f"results_{timestamp}")
        os.makedirs(results_dir, exist_ok=True)

        results_file_path = os.path.join(results_dir, "results.txt")

        # Disable the search button to prevent multiple clicks
        self.search_button.config(state=tk.DISABLED, bg="gray")
        self.status_label.config(text="Status: Search in progress...", fg="orange")

        self.search_thread = threading.Thread(target=self.search_webshops, args=(results_file_path,))
        self.search_thread.start()

    def search_webshops(self, results_file_path):
        try:
            keywords = self.load_input_file(self.keywords_file)
            payment_providers = self.load_input_file(self.payment_providers_file)

            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/85.0.4183.102 Safari/537.36"
                )
            }

            webshops_found = set()  # Store unique webshops

            with open(results_file_path, "w", encoding="utf-8") as results_file:
                for keyword in keywords:
                    encoded_keyword = requests.utils.quote(keyword)
                    base_url = f"https://www.bing.com/search?q={encoded_keyword}"
                    current_url = base_url
                    page_number = 1

                    results_file.write(f"=== Keyword: '{keyword}' ===\n")
                    self.update_live_results(f"=== Keyword: '{keyword}' ===\n")

                    while True:
                        response = requests.get(current_url, headers=headers)
                        if response.status_code != 200:
                            results_file.write(f"Failed to retrieve page {page_number} for keyword '{keyword}'.\n\n")
                            self.update_live_results(f"Failed to retrieve page {page_number} for keyword '{keyword}'.\n")
                            break

                        soup = BeautifulSoup(response.text, "html.parser")
                        results = soup.find_all("li", {"class": "b_algo"})

                        if not results:
                            results_file.write(f"No results found on page {page_number}.\n")
                            self.update_live_results(f"No results found on page {page_number}.\n")
                            break

                        for result in results:
                            link_tag = result.find("a", href=True)
                            if link_tag:
                                webshop_name = link_tag.text.strip()
                                webshop_url = link_tag['href'].strip()

                                # Avoid duplicates
                                domain = re.sub(r'https?://(www\.)?', '', webshop_url).split('/')[0]
                                if domain in webshops_found:
                                    continue
                                webshops_found.add(domain)

                                # Check for payment providers in the webshop's website
                                payment_found = self.check_payment_providers(webshop_url, payment_providers, headers)
                                if payment_found:
                                    result_line = f"URL: https://{domain}\nPayment Providers Found: {', '.join(payment_found)}\n\n"
                                    results_file.write(result_line)
                                    self.update_live_results(result_line)
                                    # Send to Telegram (excluding PayPal results)
                                    if self.telegram_messenger and 'paypal' not in payment_found:
                                        self.telegram_messenger.queue_message(result_line)

                        # Check for the "Next" page link
                        next_button = soup.find("a", {"title": "Next page"})
                        if next_button and 'href' in next_button.attrs:
                            next_page_url = "https://www.bing.com" + next_button['href']
                            current_url = next_page_url
                            page_number += 1

                            # Optional: Add delay to prevent being blocked
                            time.sleep(1)
                        else:
                            break

                    results_file.flush()

            self.root.after(0, self.update_status, f"Status: Search completed! Results saved to '{results_file_path}'", "green")
        except Exception as e:
            self.root.after(0, self.update_status, f"Status: An error occurred - {str(e)}", "red")
        finally:
            self.root.after(0, self.enable_search_button)

    def check_payment_providers(self, url, payment_providers, headers):
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                return []

            page_content = response.text.lower()
            found_providers = [pp for pp in payment_providers if pp.lower() in page_content]
            return found_providers
        except:
            return []

    def update_live_results(self, message):
        """Update the live results text box."""
        self.results_text.config(state='normal')  # Enable editing
        self.results_text.insert(tk.END, message)  # Insert new text
        self.results_text.see(tk.END)  # Scroll to the end
        self.results_text.config(state='disabled')  # Disable editing

    def update_status(self, message, color):
        self.status_label.config(text=message, fg=color)

    def enable_search_button(self):
        self.search_button.config(state=tk.NORMAL, bg="green")

    @staticmethod
    def load_input_file(file_path):
        with open(file_path, "r", encoding="utf-8") as file:
            return [line.strip() for line in file if line.strip()]


if __name__ == "__main__":
    root = tk.Tk()
    app = WebshopFinderApp(root)
    root.mainloop()
