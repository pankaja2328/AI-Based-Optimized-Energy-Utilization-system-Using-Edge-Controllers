import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

class SchedulesPage extends StatefulWidget {
  const SchedulesPage({super.key});

  @override
  State<SchedulesPage> createState() => _SchedulesPageState();
}

class _SchedulesPageState extends State<SchedulesPage> {
  Map<String, List<int>> schedules = {};
  bool loading = true;

  @override
  void initState() {
    super.initState();
    fetchSchedules();
  }

  Future<void> fetchSchedules() async {
    final response = await http.get(Uri.parse("http://10.0.2.2:5000/schedules"));
    if (response.statusCode == 200) {
      String rawData = jsonDecode(response.body)["schedules"];
      setState(() {
        schedules = parseSchedules(rawData);
        loading = false;
      });
    } else {
      setState(() {
        loading = false;
      });
    }
  }

  Map<String, List<int>> parseSchedules(String raw) {
    final Map<String, List<int>> result = {};
    final regex = RegExp(r'--- (.+?) ---\nStates: \[([0-1,\s]+)\]');
    final matches = regex.allMatches(raw);

    for (var m in matches) {
      String name = m.group(1)!.trim();
      String statesStr = m.group(2)!;
      List<int> states = statesStr.split(',').map((s) => int.parse(s.trim())).toList();
      result[name] = states;
    }
    return result;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Schedules"), backgroundColor: Colors.teal),
      body: loading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
        padding: const EdgeInsets.all(16),
        children: schedules.entries.map((entry) {
          final name = entry.key;
          final states = entry.value;

          // Extract ON hours for text display
          final onHours = List.generate(24, (i) => i).where((i) => states[i] == 1).toList();

          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(name,
                  style: const TextStyle(
                      fontSize: 18, fontWeight: FontWeight.bold)),
              const SizedBox(height: 8),

              // Row of 24 boxes
              Row(
                children: List.generate(24, (i) {
                  return Expanded(
                    child: Tooltip(
                      message: "${i}:00 - ${states[i] == 1 ? 'ON' : 'OFF'}",
                      child: Container(
                        margin: const EdgeInsets.symmetric(horizontal: 1),
                        height: 25,
                        color: states[i] == 1 ? Colors.green : Colors.grey[300],
                      ),
                    ),
                  );
                }),
              ),

              const SizedBox(height: 4),

              // Hour labels
              Row(
                children: List.generate(24, (i) {
                  return Expanded(
                    child: Text(
                      "$i",
                      textAlign: TextAlign.center,
                      style: const TextStyle(fontSize: 10),
                    ),
                  );
                }),
              ),

              const SizedBox(height: 8),

              // Text showing ON hours
              Text("ON Hours: ${onHours.join(', ')}",
                  style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w500)),

              const SizedBox(height: 16),
            ],
          );
        }).toList(),
      ),
    );
  }
}
