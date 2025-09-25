// lib/models/appliance.dart
class Appliance {
  final String name;
  final String onHours;
  final String offHours;
  final List<double> prediction; // usage predictions over time
  final String usage;   // e.g., "3.0 kWh"
  final String cost;    // e.g., "LKR 120"
  final String savings; // e.g., "LKR 30"

  Appliance({
    required this.name,
    required this.onHours,
    required this.offHours,
    required this.prediction,
    required this.usage,
    required this.cost,
    required this.savings,
  });
}
