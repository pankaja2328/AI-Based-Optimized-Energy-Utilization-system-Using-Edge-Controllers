import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:fl_chart/fl_chart.dart';

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
  }

  Future<void> fetchApplianceData() async {
    try {
      final response = await http.get(Uri.parse("http://10.0.2.2:5000/analysis"));
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        setState(() {
          appliances = data.entries.map<Map<String, dynamic>>((entry) {
            return {
              'name': entry.key,
              'original_cost': entry.value['original_cost'],
              'optimized_cost': entry.value['optimized_cost'],
              'savings': entry.value['savings'],
            };
          }).toList();

          loading = false;
        });
      } else {
        setState(() {
          appliances = [];
          loading = false;
        });
      }
    } catch (e) {
      print("Error fetching data: $e");
      setState(() {
        appliances = [];
        loading = false;
      });
    }
  }



  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Predictions"), backgroundColor: Colors.teal),
      body: loading
          ? const Center(child: CircularProgressIndicator())
          : ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: appliances.length,
        itemBuilder: (context, index) {
          final appliance = appliances[index];

          // If your Flask also sends a 'prediction' list, you can use it for the graph
          final List<double> prediction =
          appliance['prediction'] != null
              ? List<double>.from(appliance['prediction'])
              : [0, 0, 0, 0, 0];

          return Card(
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
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
                            fontSize: 18, fontWeight: FontWeight.bold),
                      ),
                      const Icon(Icons.energy_savings_leaf, color: Colors.teal),
                    ],
                  ),
                  const SizedBox(height: 12),

                  // Graph
                  SizedBox(
                    height: 50,
                    child: LineChart(
                      LineChartData(
                        gridData: FlGridData(show: true, drawVerticalLine: false),
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
                                color: Colors.teal.withOpacity(0.2)),
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
                      _buildDetail("Original", "${appliance['original_cost']} LKR"),
                      _buildDetail("Optimized", "${appliance['optimized_cost']} LKR"),
                      _buildDetail("Savings", "${appliance['savings']} LKR", color: Colors.green),
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

  Widget _buildDetail(String label, String value, {Color color = Colors.black87}) {
    return Column(
      children: [
        Text(value,
            style: TextStyle(
              fontWeight: FontWeight.bold,
              color: color,
            )),
        const SizedBox(height: 4),
        Text(label, style: const TextStyle(fontSize: 12, color: Colors.grey)),
      ],
    );
  }
}
