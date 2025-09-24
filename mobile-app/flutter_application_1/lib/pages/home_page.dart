import 'package:flutter/material.dart';
import '../widgets/stat_card.dart';
import '../widgets/power_usage_box.dart';
import 'package:fl_chart/fl_chart.dart'; // for graphs

class HomePage extends StatelessWidget {
  const HomePage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.blueGrey[100],
      appBar: AppBar(
        title: const Text("Hi Charlie"),
        backgroundColor: Colors.blueGrey[50],
        elevation: 0,
        leading: const Icon(Icons.menu),
        actions: [
          IconButton(onPressed: () {}, icon: const Icon(Icons.logout))
        ],
      ),
      body: Column(
        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
        children: [
          // Box 1: Power Usage
            const PowerUsageBox(usagePercent: 0.65),


          // 65% example

          // Box 2: 2x2 stats grid
          Container(
            height: 350,
            width: 400,
            padding: const EdgeInsets.all(8),
            child: GridView.count(
              crossAxisCount: 2,
              crossAxisSpacing: 10,
              mainAxisSpacing: 10,
              childAspectRatio: 1.2,
              children: const [
                StatCard(
                  title: "Energy Saved",
                  icon: Icons.bolt,
                  value: "120 kWh",
                  color: Colors.green,
                ),
                StatCard(
                  title: "Energy Consumed",
                  icon: Icons.energy_savings_leaf,
                  value: "450 kWh",
                  color: Colors.red,
                ),
                StatCard(
                  title: "Unit Pricing",
                  icon: Icons.attach_money,
                  value: "\$0.15 /kWh",
                  color: Colors.blue,
                ),
                StatCard(
                  title: "Unit Cost Saved",
                  icon: Icons.savings,
                  value: "\$35",
                  color: Colors.orange,
                ),
              ],
            ),
          ),

          // Box 3: Graph
          Container(
            height: 250,
            width: 400,
            padding: const EdgeInsets.all(8),
            child: Card(
              shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12)),
              elevation: 2,
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    const Text(
                      "Consumption Prediction",
                      style:
                      TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 12),
                    Expanded(
                      child: LineChart(
                        LineChartData(
                          gridData: FlGridData(show: true),
                          titlesData: FlTitlesData(show: true),
                          borderData: FlBorderData(show: true),
                          lineBarsData: [
                            LineChartBarData(
                              spots: const [
                                FlSpot(0, 2),
                                FlSpot(1, 3),
                                FlSpot(2, 1.5),
                                FlSpot(3, 4),
                                FlSpot(4, 3.2),
                                FlSpot(5, 5),
                              ],
                              isCurved: true,
                              barWidth: 3,
                              color: Colors.blue,
                              dotData: FlDotData(show: false),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
