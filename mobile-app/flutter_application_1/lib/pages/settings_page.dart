import 'package:flutter/material.dart';
import 'account_page.dart';
import 'contact_us_page.dart';
import 'terms_page.dart';
import 'privacy_page.dart';
import 'about_page.dart';
import 'logout_page.dart';

class SettingsPage extends StatelessWidget {
  const SettingsPage({super.key});

  void _navigateTo(BuildContext context, Widget page) {
    Navigator.push(
      context,
      MaterialPageRoute(builder: (context) => page),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Settings"),
        backgroundColor: Colors.teal,
        elevation: 0,
      ),
      body: ListView(
        children: [
          _buildSettingTile(
            context,
            title: "Account",
            icon: Icons.person,
            page: const AccountPage(),
          ),
          _buildSettingTile(
            context,
            title: "Contact Us",
            icon: Icons.contact_mail,
            page: const ContactUsPage(),
          ),
          _buildSettingTile(
            context,
            title: "Terms & Conditions",
            icon: Icons.article,
            page: const TermsPage(),
          ),
          _buildSettingTile(
            context,
            title: "Privacy Policy",
            icon: Icons.privacy_tip,
            page: const PrivacyPage(),
          ),
          _buildSettingTile(
            context,
            title: "About",
            icon: Icons.info,
            page: const AboutPage(),
          ),
          _buildSettingTile(
            context,
            title: "Logout",
            icon: Icons.logout,
            page: const LogoutPage(),
          ),
        ],
      ),
    );
  }

  Widget _buildSettingTile(
      BuildContext context, {
        required String title,
        required IconData icon,
        required Widget page,
      }) {
    return ListTile(
      leading: Icon(icon, color: Colors.blueGrey),
      title: Text(title),
      trailing: const Icon(Icons.arrow_forward_ios, size: 16),
      onTap: () => _navigateTo(context, page),
    );
  }
}
