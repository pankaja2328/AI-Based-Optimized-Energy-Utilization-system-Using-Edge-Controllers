import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:fl_chart/fl_chart.dart';
import 'dart:async';

class PredictionsPage extends StatefulWidget {
  const PredictionsPage({super.key});

  @override
  State<PredictionsPage> createState() => _PredictionsPageState();
}

class _PredictionsPageState extends State<PredictionsPage> {
  List<Map<String, dynamic>> appliances = [];
  bool loading = true;

  @override
  void initState() {
    super.initState();
    fetchApplianceData();

    // re-fetch every 30 minutes
    Timer.periodic(Duration(minutes: 30), (timer) {
      fetchApplianceData();
    });
  }

  Future<void> fetchApplianceData() async {
    try {
      final response = await http.get(
        Uri.parse("https://web-production-543c4.up.railway.app/analysis"),
      );
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        if (data is Map<String, dynamic>) {
          setState(() {
            appliances = data.entries.map<Map<String, dynamic>>((entry) {
              final value = entry.value;
              return {
                'name': entry.key,
                'original_cost': value != null && value['original_cost'] != null
                    ? value['original_cost']
                    : 0,
                'optimized_cost':
                    value != null && value['optimized_cost'] != null
                    ? value['optimized_cost']
                    : 0,
                'savings': value != null && value['savings'] != null
                    ? value['savings']
                    : 0,
                // optional: 'prediction': value['prediction'],
              };
            }).toList();
            loading = false;
          });
        } else {
          print(
            "Unexpected /analysis response type: ${data.runtimeType} -> $data",
          );
          setState(() {
            appliances = [];
            loading = false;
          });
        }
      } else {
        print("analysis returned ${response.statusCode}: ${response.body}");
        setState(() {
          appliances = [];
          loading = false;
        });
      }
    } catch (e, st) {
      print("Error fetching data: $e\n$st");
      setState(() {
        appliances = [];
        loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Predictions"),
        backgroundColor: Colors.teal,
      ),
      body: loading
          ? const Center(child: CircularProgressIndicator())
          : ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: appliances.length,
              itemBuilder: (context, index) {
                final appliance = appliances[index];

                // If your Flask also sends a 'prediction' list, you can use it for the graph
                final List<double> prediction = appliance['prediction'] != null
                    ? List<double>.from(appliance['prediction'])
                    : [0, 0, 0, 0, 0];

                return Card(
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(16),
                  ),
                  elevation: 5,
                  margin: const EdgeInsets.only(bottom: 16),
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // Appliance Title
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text(
                              appliance['name'],
                              style: const TextStyle(
                                fontSize: 18,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            const Icon(
                              Icons.energy_savings_leaf,
                              color: Colors.teal,
                            ),
                          ],
                        ),
                        const SizedBox(height: 12),

                        // Graph
                        SizedBox(
                          height: 50,
                          child: LineChart(
                            LineChartData(
                              gridData: FlGridData(
                                show: true,
                                drawVerticalLine: false,
                              ),
                              titlesData: FlTitlesData(show: false),
                              borderData: FlBorderData(show: false),
                              lineBarsData: [
                                LineChartBarData(
                                  spots: List.generate(
                                    prediction.length,
                                    (i) => FlSpot(i.toDouble(), prediction[i]),
                                  ),
                                  isCurved: true,
                                  color: Colors.teal,
                                  dotData: FlDotData(show: false),
                                  belowBarData: BarAreaData(
                                    show: true,
                                    color: Colors.teal.withValues(alpha: 0.2),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                        const SizedBox(height: 12),

                        // Costs and Savings
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            _buildDetail(
                              "Original",
                              "${appliance['original_cost']} LKR",
                            ),
                            _buildDetail(
                              "Optimized",
                              "${appliance['optimized_cost']} LKR",
                            ),
                            _buildDetail(
                              "Savings",
                              "${appliance['savings']} LKR",
                              color: Colors.green,
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
    );
  }

  Widget _buildDetail(
    String label,
    String value, {
    Color color = Colors.black87,
  }) {
    return Column(
      children: [
        Text(
          value,
          style: TextStyle(fontWeight: FontWeight.bold, color: color),
        ),
        const SizedBox(height: 4),
        Text(label, style: const TextStyle(fontSize: 12, color: Colors.grey)),
      ],
    );
  }
}
