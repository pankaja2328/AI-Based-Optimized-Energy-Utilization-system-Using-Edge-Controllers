// lib/pages/schedules_page.dart
import 'package:flutter/material.dart';
import '../data/appliance_data.dart';
import '../models/appliance.dart';

class SchedulesPage extends StatefulWidget {
  const SchedulesPage({super.key});

  @override
  State<SchedulesPage> createState() => _SchedulesPageState();
}

class _SchedulesPageState extends State<SchedulesPage> {
  void _addApplianceDialog() {
    final nameController = TextEditingController();
    final onController = TextEditingController();
    final offController = TextEditingController();

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text("Add Appliance"),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: nameController,
              decoration: const InputDecoration(labelText: "Appliance Name"),
            ),
            TextField(
              controller: onController,
              decoration: const InputDecoration(labelText: "On Hours"),
            ),
            TextField(
              controller: offController,
              decoration: const InputDecoration(labelText: "Off Hours"),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text("Cancel"),
          ),
          ElevatedButton(
            onPressed: () {
              setState(() {
                appliances.add(
                  Appliance(
                    name: nameController.text,
                    onHours: onController.text,
                    offHours: offController.text,
                    prediction: [1.0, 1.2, 1.3, 1.1, 1.4], // dummy default
                    usage: "1.2 kWh",
                    cost: "LKR 50",
                    savings: "LKR 10",
                  ),
                );
              });
              Navigator.pop(context);
            },
            child: const Text("Add"),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.blueGrey[50],
      appBar: AppBar(
        title: const Text(
          "Appliance Schedules",
          style: TextStyle(color: Colors.black87),
        ),
        backgroundColor: Colors.teal,
        elevation: 0,
      ),
      body: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        child: Column(
          children: [
            Expanded(
              child: ListView.separated(
                itemCount: appliances.length,
                separatorBuilder: (context, index) =>
                const SizedBox(height: 12),
                itemBuilder: (context, index) {
                  final Appliance appliance = appliances[index];
                  return Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(16),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black12,
                          blurRadius: 8,
                          offset: const Offset(0, 4),
                        ),
                      ],
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(appliance.name,
                            style: const TextStyle(
                                fontSize: 16, fontWeight: FontWeight.bold)),
                        const SizedBox(height: 8),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text("On hours: ${appliance.onHours}",
                                style: const TextStyle(fontSize: 14)),
                            Text("Off hours: ${appliance.offHours}",
                                style: const TextStyle(fontSize: 14)),
                          ],
                        ),
                      ],
                    ),
                  );
                },
              ),
            ),
            const SizedBox(height: 12),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                onPressed: _addApplianceDialog,
                icon: const Icon(Icons.add),
                label: const Text(
                  "Add Appliance",
                  style: TextStyle(fontSize: 16),
                ),
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(16),
                  ),
                  backgroundColor: Colors.blueGrey[200],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
