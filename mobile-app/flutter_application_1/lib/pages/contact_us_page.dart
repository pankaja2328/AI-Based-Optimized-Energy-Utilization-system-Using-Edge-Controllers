import 'package:flutter/material.dart';

class ContactUsPage extends StatelessWidget {
  const ContactUsPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Contact Us"),
        backgroundColor: Colors.teal,
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: const [
            Text("Need help?", style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            SizedBox(height: 10),
            Text("📧 Email: support@energyapp.com", style: TextStyle(fontSize: 16)),
            SizedBox(height: 8),
            Text("📞 Phone: +1 800 123 4567", style: TextStyle(fontSize: 16)),
            SizedBox(height: 8),
            Text("🌐 Website: www.energyapp.com", style: TextStyle(fontSize: 16)),
          ],
        ),
      ),
    );
  }
}
