import 'package:flutter/material.dart';

class PowerUsageBox extends StatelessWidget {
  final double usagePercent; // value between 0 and 1

  const PowerUsageBox({super.key, required this.usagePercent});

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 150,
      width: 400,
      padding: const EdgeInsets.all(16),
      child: Card(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        elevation: 2,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.power, size: 40, color: Colors.blue),
              const SizedBox(height: 10),
              const Text(
                "Power Usage",
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 10),
              LinearProgressIndicator(
                value: usagePercent,
                minHeight: 10,
                backgroundColor: Colors.grey[300],
                color: Colors.blue,
              ),
              const SizedBox(height: 6),
              Text("${(usagePercent * 100).toStringAsFixed(0)}%"),
            ],
          ),
        ),
      ),
    );
  }
}
