import 'package:flutter/material.dart';

void main() {
  runApp(const MyApp());
}


 class MyApp extends StatelessWidget{
   const MyApp({super.key});

   @override
   Widget build(BuildContext context){
     return MaterialApp(
       debugShowCheckedModeBanner: false,
       home: Scaffold(
         backgroundColor: Colors.blueGrey[100],
         appBar: AppBar(
           title: Text("Hi Charlie"),
           backgroundColor: Colors.blueGrey[50],
           elevation: 0,
           leading: Icon(Icons.menu),
           actions:
             [IconButton(onPressed: () {}, icon: Icon(Icons.logout))],
         ),
           body: Center(
           child: Container(
           height: 100,
           width:400,
           decoration: BoxDecoration(
             color:Colors.grey[300],
             borderRadius: BorderRadius.circular(20),
           ),
           padding: EdgeInsets.all(25),
             child: Text("Hi User!",
                 style: TextStyle(
                   color: Colors.black,
                   fontSize: 24
                 )),

             //   child: Icon(
             //   Icons.favorite,
             //   color: Colors.black,
             //   size: 64,
             // )

          )
         )
       )
     ); //MaterialApp
   }
 }