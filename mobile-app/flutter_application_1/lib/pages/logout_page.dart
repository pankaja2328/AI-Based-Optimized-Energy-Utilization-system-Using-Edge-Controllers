import 'package:flutter/material.dart';

class LogoutPage extends StatelessWidget {
  const LogoutPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Logout"),
        backgroundColor: Colors.blueGrey[50],
      ),
      body: const Center(
        child: Text(
          "You have been logged out (Demo)",
          style: TextStyle(fontSize: 18, color: Colors.red),
        ),
      ),
    );
  }
}
