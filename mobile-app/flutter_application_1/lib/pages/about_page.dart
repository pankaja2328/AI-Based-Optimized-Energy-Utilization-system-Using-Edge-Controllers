import 'package:flutter/material.dart';

class AboutPage extends StatelessWidget {
  const AboutPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("About"),
        backgroundColor: Colors.teal,
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: ListView(
          children: const [
            Text(
              "About This App",
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            SizedBox(height: 10),
            Text(
              "The AI-Based Optimized Energy Utilization System is designed to help "
                  "households and businesses monitor, schedule, and optimize their energy usage. "
                  "Using AI-powered predictions, the app suggests ways to save on electricity bills "
                  "and reduce unnecessary energy consumption.",
              style: TextStyle(fontSize: 16),
            ),
            SizedBox(height: 16),
            Text(
              "Features:",
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
            ),
            SizedBox(height: 8),
            Text("• Real-time power usage monitoring",
                style: TextStyle(fontSize: 16)),
            Text("• Smart scheduling for appliances",
                style: TextStyle(fontSize: 16)),
            Text("• Cost and savings predictions",
                style: TextStyle(fontSize: 16)),
            Text("• Secure and user-friendly design",
                style: TextStyle(fontSize: 16)),
            SizedBox(height: 16),
            Text(
              "Version: 1.0.0",
              style: TextStyle(fontSize: 16, fontStyle: FontStyle.italic),
            ),
            SizedBox(height: 8),
            Text(
              "Developed by: Isuru Indrajith",
              style: TextStyle(fontSize: 16),
            ),
          ],
        ),
      ),
    );
  }
}
