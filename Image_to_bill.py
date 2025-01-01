import os
import sys
import tkinter as tk
from tkinter import messagebox, filedialog
import math
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import cv2
import easyocr
from PIL import Image, ImageTk

class MeasurementRow:
    # [Previous MeasurementRow class implementation remains unchanged]
    def __init__(self, parent, row_num, on_update, on_filled):
        self.parent = parent
        self.row_num = row_num
        self.on_update = on_update
        self.on_filled = on_filled
        
        self.frame = tk.Frame(parent)
        self.frame.grid(row=row_num, column=0, columnspan=7, pady=2, sticky="w")
        
        tk.Label(self.frame, text=f"Row {row_num + 1}:", width=10, anchor="w").grid(row=0, column=0, padx=(5,15))
        
        self.length_var = tk.StringVar()
        self.width_var = tk.StringVar()
        self.amount_var = tk.StringVar()
        
        self.length_entry = tk.Entry(self.frame, width=20, textvariable=self.length_var)
        self.length_entry.grid(row=0, column=1, padx=(0,20))
        
        self.width_entry = tk.Entry(self.frame, width=20, textvariable=self.width_var)
        self.width_entry.grid(row=0, column=2, padx=(0,20))
        
        self.amount_entry = tk.Entry(self.frame, width=20, textvariable=self.amount_var)
        self.amount_entry.grid(row=0, column=3, padx=(0,20))
        
        self.orig_sqft_label = tk.Label(self.frame, text="0.000 sq ft", width=25, anchor="e")
        self.adj_sqft_label = tk.Label(self.frame, text="0.000 sq ft", width=25, anchor="e")
        self.price_label = tk.Label(self.frame, text="Rs. 0.00", width=20, anchor="e")
        
        self.orig_sqft_label.grid(row=0, column=4, padx=(0,20))
        self.adj_sqft_label.grid(row=0, column=5, padx=(0,20))
        self.price_label.grid(row=0, column=6, padx=(0,5))
        
        self.length_var.trace('w', self.check_if_filled)
        self.width_var.trace('w', self.check_if_filled)
        self.amount_var.trace('w', self.check_if_filled)

    def check_if_filled(self, *args):
        if (self.length_var.get() and 
            self.width_var.get() and 
            self.amount_var.get()):
            self.on_filled()

    def calculate(self, price_per_feet):
        try:
            length = float(self.length_var.get())
            width = float(self.width_var.get())
            amount = float(self.amount_var.get())
            
            adj_length = adjust_measurement(length)
            adj_width = adjust_measurement(width)
            
            orig_sqft = (length * width) / 144
            adj_sqft = (adj_length * adj_width) / 144
            total = adj_sqft * amount * price_per_feet
            
            self.orig_sqft_label.config(text=f"{orig_sqft:.3f} sq ft")
            self.adj_sqft_label.config(text=f"{adj_sqft:.3f} sq ft")
            self.price_label.config(text=f" Rs. {total:.2f}")
            
            return total
        except ValueError:
            return 0

class GlassCalculator:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Glass Price Calculator")
        
        # Main container
        self.container = tk.Frame(self.root)
        self.container.pack(fill=tk.BOTH, expand=True)
        
        # Input frame (fixed at top)
        self.input_frame = tk.LabelFrame(self.container, text="Price Setting", padx=10, pady=5)
        self.input_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(self.input_frame, text="Price per Sq-Feet (Rs.):", anchor="w").grid(row=0, column=0, padx=5, pady=5)
        self.price_entry = tk.Entry(self.input_frame, width=15)
        self.price_entry.grid(row=0, column=1, padx=5, pady=5)
        self.price_entry.insert(0, "0")
        
        tk.Label(self.input_frame, text="Glass Name:", anchor="w").grid(row=0, column=2, padx=5, pady=5)
        self.glass_name_entry = tk.Entry(self.input_frame, width=15)
        self.glass_name_entry.grid(row=0, column=3, padx=5, pady=5)
        
        # Image upload button
        self.upload_button = tk.Button(self.input_frame, text="Upload Image", command=self.upload_image)
        self.upload_button.grid(row=0, column=4, padx=5, pady=5)
        
        # Measurements frame with scrollbar
        self.measurements_outer_frame = tk.LabelFrame(self.container, text="Measurements", padx=10, pady=5)
        self.measurements_outer_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Create canvas and scrollbar for measurements
        self.canvas = tk.Canvas(self.measurements_outer_frame)
        self.scrollbar = tk.Scrollbar(self.measurements_outer_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.measurements_frame = tk.Frame(self.canvas)
        
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # Pack scrollable components
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Create window in canvas
        self.canvas_frame = self.canvas.create_window((0, 0), window=self.measurements_frame, anchor="nw")
        
        # Configure canvas scrolling
        self.measurements_frame.bind("<Configure>", self.on_frame_configure)
        self.canvas.bind("<Configure>", self.on_canvas_configure)
        
        # Headers
        headers = [
            ("Row", 10, "w", (5,15)),
            ("Length (Inc)", 15, "w", (0,20)),
            ("Width (Inc)", 15, "w", (0,20)),
            ("Quantity", 15, "w", (0,20)),
            ("Original Sq ft", 20, "e", (0,20)),
            ("Sq ft", 20, "e", (0,20)),
            ("Price", 15, "e", (0,5))
        ]
        
        for col, (header, width, anchor, pad) in enumerate(headers):
            lbl = tk.Label(
                self.measurements_frame,
                text=header,
                font=("Arial", 10, "bold"),
                width=width,
                anchor=anchor
            )
            lbl.grid(row=0, column=col, padx=pad, pady=5)
        
        self.rows = []
        self.add_row()
        
        # Total frame (fixed at bottom)
        self.total_frame = tk.LabelFrame(self.container, text="Total", padx=10, pady=5)
        self.total_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.total_label = tk.Label(
            self.total_frame, 
            text="Total Price: Rs. 0.00", 
            font=("Arial", 12, "bold"),
            anchor="w"
        )
        self.total_label.pack(pady=5)
        
        # Buttons frame
        self.buttons_frame = tk.Frame(self.container)
        self.buttons_frame.pack(pady=10)
        
        self.calculate_button = tk.Button(
            self.buttons_frame, 
            text="Calculate", 
            command=self.calculate_total,
            width=10
        )
        self.calculate_button.pack(side=tk.LEFT, padx=5)
        
        self.pdf_button = tk.Button(
            self.buttons_frame, 
            text="Generate PDF", 
            command=self.generate_pdf,
            width=10
        )
        self.pdf_button.pack(side=tk.LEFT, padx=5)
        
        # Rules label
        rules_text = """Measurement Rule : Aditya Aluminium & Glass Company"""
        rules_label = tk.Label(self.container, text=rules_text, justify=tk.LEFT, font=("Arial", 10))
        rules_label.pack(pady=10)

    def on_frame_configure(self, event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_frame, width=event.width)

    def add_row(self):
        new_row = MeasurementRow(
            self.measurements_frame,
            len(self.rows) + 1,
            self.calculate_total,
            self.on_row_filled
        )
        self.rows.append(new_row)
    
    def on_row_filled(self):
        if all(row.length_var.get() and row.width_var.get() and row.amount_var.get() 
               for row in self.rows):
            self.add_row()
    
    def calculate_total(self):
        try:
            price_per_feet = float(self.price_entry.get())
            total = sum(row.calculate(price_per_feet) for row in self.rows)
            self.total_label.config(text=f"Total Price: Rs. {total:.2f}")
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter valid numeric values!")
    
    def generate_pdf(self):
        try:
            price_per_feet = float(self.price_entry.get())
            total = sum(row.calculate(price_per_feet) for row in self.rows)
            glass_name = self.glass_name_entry.get()
            
            # Get the directory where the .exe file is located
            if getattr(sys, 'frozen', False):
                # Running as a .exe file
                exe_dir = os.path.dirname(sys.executable)
            else:
                # Running as a script
                exe_dir = os.path.dirname(os.path.abspath(__file__))
            
            # Define the PDF file path
            pdf_path = os.path.join(exe_dir, f"{glass_name}.pdf")
            
            # Generate the PDF
            pdf = canvas.Canvas(pdf_path, pagesize=letter)
            pdf.setFont("Helvetica-Bold", 16)
            pdf.drawString(250, 750, "BILL")
            
            pdf.setFont("Helvetica", 12)
            pdf.drawString(50, 730, f"Glass Name: {glass_name}")
            
            pdf.drawString(50, 700, "S.NO")
            pdf.drawString(100, 700, "Length (Inc)")
            pdf.drawString(200, 700, "Width (Inc)")
            pdf.drawString(300, 700, "Quantity")
            pdf.drawString(400, 700, "Sq ft")
            pdf.drawString(500, 700, "Price")
            
            y = 680
            serial_number = 1
            for row in self.rows:
                if row.length_var.get() and row.width_var.get() and row.amount_var.get():
                    y -= 20
                    pdf.drawString(50, y, f"{serial_number}")
                    pdf.drawString(100, y, row.length_var.get())
                    pdf.drawString(200, y, row.width_var.get())
                    pdf.drawString(300, y, row.amount_var.get())
                    pdf.drawString(400, y, row.adj_sqft_label.cget("text"))
                    pdf.drawString(500, y, row.price_label.cget("text"))
                    serial_number += 1
            
            pdf.drawString(50, y - 40, f"Total Price: Rs. {total:.2f}")
            pdf.save()
            messagebox.showinfo("PDF Generated", f"PDF has been generated successfully!\nSaved at: {pdf_path}")
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter valid numeric values!")
    
    def upload_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")])
        if file_path:
            # Initialize EasyOCR reader
            reader = easyocr.Reader(['en'])  # Use 'en' for English
            # Read the image
            result = reader.readtext(file_path)
            # Process the extracted text
            extracted_text = " ".join([text for (_, text, _) in result])
            self.process_extracted_text(extracted_text)
    
    def process_extracted_text(self, text):
        # Example: Extract length, width, and quantity from the text
        # This is a simple example, you may need to implement more complex logic
        lines = text.split('\n')
        extracted_data = []
        for line in lines:
            if 'length' in line.lower() and 'width' in line.lower() and 'quantity' in line.lower():
                parts = line.split()
                length = parts[1]
                width = parts[3]
                quantity = parts[5]
                extracted_data.append((length, width, quantity))
        
        if extracted_data:
            self.show_extracted_data(extracted_data)
        else:
            messagebox.showinfo("No Data Found", "No valid data was extracted from the image.")
    
    def show_extracted_data(self, extracted_data):
        # Create a new window to display extracted data and PDF preview
        self.preview_window = tk.Toplevel(self.root)
        self.preview_window.title("Extracted Data and PDF Preview")
        
        # Display extracted data
        data_frame = tk.LabelFrame(self.preview_window, text="Extracted Data", padx=10, pady=10)
        data_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        for i, (length, width, quantity) in enumerate(extracted_data):
            row_frame = tk.Frame(data_frame)
            row_frame.pack(fill=tk.X, pady=2)
            
            tk.Label(row_frame, text=f"Row {i + 1}:", width=10, anchor="w").pack(side=tk.LEFT, padx=(5,15))
            tk.Label(row_frame, text=f"Length: {length}", width=15, anchor="w").pack(side=tk.LEFT, padx=(0,20))
            tk.Label(row_frame, text=f"Width: {width}", width=15, anchor="w").pack(side=tk.LEFT, padx=(0,20))
            tk.Label(row_frame, text=f"Quantity: {quantity}", width=15, anchor="w").pack(side=tk.LEFT, padx=(0,20))
        
        # PDF Preview (simulated)
        preview_frame = tk.LabelFrame(self.preview_window, text="PDF Preview", padx=10, pady=10)
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        preview_text = tk.Text(preview_frame, wrap=tk.WORD, height=10)
        preview_text.pack(fill=tk.BOTH, expand=True)
        
        # Simulate PDF content
        preview_text.insert(tk.END, "BILL\n\n")
        preview_text.insert(tk.END, f"Glass Name: {self.glass_name_entry.get()}\n\n")
        preview_text.insert(tk.END, "S.NO\tLength (Inc)\tWidth (Inc)\tQuantity\tSq ft\tPrice\n")
        for i, (length, width, quantity) in enumerate(extracted_data):
            preview_text.insert(tk.END, f"{i + 1}\t{length}\t{width}\t{quantity}\t0.000 sq ft\tRs. 0.00\n")
        preview_text.insert(tk.END, f"\nTotal Price: Rs. 0.00")
        
        # Buttons
        button_frame = tk.Frame(self.preview_window)
        button_frame.pack(pady=10)
        
        generate_pdf_button = tk.Button(button_frame, text="Generate PDF", command=lambda: self.generate_pdf_from_preview(extracted_data))
        generate_pdf_button.pack(side=tk.LEFT, padx=5)
        
        go_back_button = tk.Button(button_frame, text="Go Back", command=self.preview_window.destroy)
        go_back_button.pack(side=tk.LEFT, padx=5)
    
    def generate_pdf_from_preview(self, extracted_data):
        try:
            price_per_feet = float(self.price_entry.get())
            glass_name = self.glass_name_entry.get()
            
            # Get the directory where the .exe file is located
            if getattr(sys, 'frozen', False):
                # Running as a .exe file
                exe_dir = os.path.dirname(sys.executable)
            else:
                # Running as a script
                exe_dir = os.path.dirname(os.path.abspath(__file__))
            
            # Define the PDF file path
            pdf_path = os.path.join(exe_dir, f"{glass_name}.pdf")
            
            # Generate the PDF
            pdf = canvas.Canvas(pdf_path, pagesize=letter)
            pdf.setFont("Helvetica-Bold", 16)
            pdf.drawString(250, 750, "BILL")
            
            pdf.setFont("Helvetica", 12)
            pdf.drawString(50, 730, f"Glass Name: {glass_name}")
            
            pdf.drawString(50, 700, "S.NO")
            pdf.drawString(100, 700, "Length (Inc)")
            pdf.drawString(200, 700, "Width (Inc)")
            pdf.drawString(300, 700, "Quantity")
            pdf.drawString(400, 700, "Sq ft")
            pdf.drawString(500, 700, "Price")
            
            y = 680
            total = 0
            for i, (length, width, quantity) in enumerate(extracted_data):
                y -= 20
                length_val = float(length)
                width_val = float(width)
                quantity_val = float(quantity)
                
                adj_length = adjust_measurement(length_val)
                adj_width = adjust_measurement(width_val)
                adj_sqft = (adj_length * adj_width) / 144
                row_total = adj_sqft * quantity_val * price_per_feet
                total += row_total
                
                pdf.drawString(50, y, f"{i + 1}")
                pdf.drawString(100, y, length)
                pdf.drawString(200, y, width)
                pdf.drawString(300, y, quantity)
                pdf.drawString(400, y, f"{adj_sqft:.3f} sq ft")
                pdf.drawString(500, y, f"Rs. {row_total:.2f}")
            
            pdf.drawString(50, y - 40, f"Total Price: Rs. {total:.2f}")
            pdf.save()
            messagebox.showinfo("PDF Generated", f"PDF has been generated successfully!\nSaved at: {pdf_path}")
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter valid numeric values!")

    def run(self):
        self.root.mainloop()

def adjust_measurement(value):
    """Adjust measurement according to given rules"""
    if 1 <= value <= 3: return 3
    elif 3 < value <= 6: return 6
    elif 6 < value <= 9: return 9
    elif 9 < value <= 12: return 12
    elif 12 <= value <= 15: return 15
    elif 15 <= value <= 18: return 18
    elif 18 < value <= 24: return 24
    elif 24 < value <= 30: return 30
    elif 30 < value <= 36: return 36
    elif 36 < value <= 42: return 42
    elif 42 < value <= 46: return 46
    elif 46 < value <= 52: return 52
    elif 52 < value <= 56: return 56
    elif 56 < value <= 60: return 60
    elif 60 < value <= 72: return 72
    elif 72 < value <= 84: return 84
    elif 84 < value <= 96: return 96
    elif 96 < value <= 108: return 108
    elif 108 < value <= 120: return 120
    else: return value

if __name__ == "__main__":
    app = GlassCalculator()
    app.run()