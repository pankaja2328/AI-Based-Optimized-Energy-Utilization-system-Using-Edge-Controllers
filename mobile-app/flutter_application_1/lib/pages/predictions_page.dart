// lib/pages/predictions_page.dart
import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import '../data/appliance_data.dart';
import '../models/appliance.dart';

class PredictionsPage extends StatelessWidget {
  const PredictionsPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Predictions"),
        backgroundColor: Colors.teal,
      ),
      body: ListView.builder(
        padding: const EdgeInsets.all(12),
        itemCount: appliances.length,
        itemBuilder: (context, index) {
          final Appliance appliance = appliances[index];
          return Card(
            shape:
            RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            elevation: 5,
            margin: const EdgeInsets.only(bottom: 16),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Appliance title
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(appliance.name,
                          style: const TextStyle(
                              fontSize: 18, fontWeight: FontWeight.bold)),
                      const Icon(Icons.energy_savings_leaf, color: Colors.teal),
                    ],
                  ),
                  const SizedBox(height: 12),

                  // Graph
                  SizedBox(
                    height: 150,
                    child: LineChart(
                      LineChartData(
                        gridData:
                        FlGridData(show: true, drawVerticalLine: false),
                        titlesData: FlTitlesData(show: false),
                        borderData: FlBorderData(show: false),
                        lineBarsData: [
                          LineChartBarData(
                            spots: List.generate(
                              appliance.prediction.length,
                                  (i) => FlSpot(
                                  i.toDouble(), appliance.prediction[i]),
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

                  // Usage details
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      _buildDetail("Usage", appliance.usage, Icons.bolt),
                      _buildDetail("Cost", appliance.cost, Icons.currency_rupee),
                      _buildDetail("Savings", appliance.savings, Icons.savings),
                    ],
                  )
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _buildDetail(String label, String value, IconData icon) {
    return Column(
      children: [
        Icon(icon, color: Colors.teal, size: 20),
        const SizedBox(height: 4),
        Text(value, style: const TextStyle(fontWeight: FontWeight.bold)),
        Text(label, style: const TextStyle(fontSize: 12, color: Colors.grey)),
      ],
    );
  }
}
