import 'package:flutter/material.dart';

class TermsPage extends StatelessWidget {
  const TermsPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Terms & Conditions"),
        backgroundColor: Colors.teal,
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: ListView(
          children: const [
            Text(
              "Terms & Conditions",
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            SizedBox(height: 10),
            Text(
              "1. Use of this app is for personal energy monitoring and scheduling only.\n"
                  "2. Users are responsible for the accuracy of the appliance schedules they enter.\n"
                  "3. The app provides predictions based on available data but does not guarantee exact results.\n"
                  "4. We may update features and policies without prior notice.\n"
                  "5. Continued use of the app constitutes agreement with these terms.",
              style: TextStyle(fontSize: 16),
            ),
          ],
        ),
      ),
    );
  }
}
